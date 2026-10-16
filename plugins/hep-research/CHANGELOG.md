# Changelog — hep-research

Release notes for the plugin. Each entry says what changed in behavior; evidence is in [VALIDATION.md](VALIDATION.md).
Software checks establish contract consistency only, not physical validity.

## Unreleased

- New `core/evidence/query.py` (v6.3 D02): bounded, pageable rows of a source and claim ledger, one per (claim, cited
  source), each with claim and source IDs, scope, `verification_date`, verification level and strength, location and
  the record position in each file. The ledger is checked with `core/evidence/ledger.py` first and a ledger with
  errors serves no rows (exit 1). Pages hold at most 20 rows and 16 KiB of JSON (product defaults, not measurements),
  report the total match count and an index digest, and give a cursor bound to that digest and the query: a cursor
  used after the ledger changed or with another query is refused (`query.stale_cursor`, `query.cursor_mismatch`,
  exit 2). A row larger than the cap is not cut; the page names the exact command that fetches it. Its CLI runs under
  the protected-mode guard like `ledger.py`. Measurements: `docs/dev/v6.3/m0-budget.md`.
- New optional adapter `adapters/cr-propagation` 0.1.0 (owner hep-computing, required by no skill; adapter status
  `proposed` because GALPROP and USINE are `proposed`). DRAGON2 is `tested-in-declared-environment`: commit cd588707 of
  cosmicrays/DRAGON2-Beta_version built from source on E2 (Homebrew GCC 15.2.0, GSL 2.8, CFITSIO 4.6.4; no system-wide
  installation). `dragon2_run.py` builds a run directory from a JSON run spec (XML, source.param, links to the data
  tables, an optional replacement production-cross-section table), runs DRAGON2 and records a `computational-run`
  (input hashes, program and commit, command, environment manifest, exit status, output hash); exit 3 without the
  binary or data. `dragon2_to_prediction.py` turns one run into one grid-node `prediction` (`representation: "grid"`,
  the node in `parameter_point`, a ratio of summed species averaged uniformly in ln(E/n) over the requested bins, no
  extrapolation) that the comparison gate and `covariance_fit.py` model `tabulated-grid` use unchanged.
- Limit benchmark of DRAGON2 against the 1D thin-disc closed form of `theory:cr-secondary-ratio` (convection,
  reacceleration, energy losses and decay off; the profile's illustrative production cross sections substituted through
  DRAGON2's data table), criteria committed before the comparison: the B/C slope over 100–1000 GeV/n agrees (0.006,
  tolerance 0.05), the absolute B/C agrees within the declared 30% (DRAGON2 9–12% higher, mostly its fixed helium
  target) and a five-node D0 grid of DRAGON2 runs recovers a sixth run's D0 within 2% through `tabulated-grid`; the D0/L
  degeneracy fails at L = 8 kpc (15–18%, tolerance 10%) because of the radial boundary at 20 kpc and the radial gas
  structure. Diagnostic runs with the boundary at 60 kpc and the gas made uniform in R (a local patch of DRAGON2,
  recorded with the runs) reach the closed form: within 2% between L = 2, 4 and 8 kpc and within 5% in absolute B/C
  once DRAGON2's helium production term is divided out. The tests replay fourteen recorded runs offline and assert what
  is established; a live rerun runs with `HEP_DRAGON2_LIVE_TEST=1`. Global propagation fits that run a code stay
  outside v1.
- `dragon2_to_prediction.py` multiplies each DRAGON2 column by its mass number A before forming a ratio: DRAGON2 writes
  its internal density per total kinetic energy (`GetFluxAtSunPosition` computes `weight = A` but does not apply it;
  the spallation source carries A_parent / A_daughter), so a ratio of species with different A was wrong (B/C 12/11
  too high, O/C 12/16 too low). The first version of the limit benchmark reported this as an unexplained 32–34% B/C
  excess (C1 failing); C1 now passes with its declared tolerance (plan amendment of 2026-10-16, a unit correction).
- Fix: `covariance_fit.py` model `tabulated-grid` no longer crashes when the best fit lies inside the first or last
  cell of a grid axis. The Fisher-matrix step was one cell, and where a full cell did not fit on one side it took a
  one-sided second-order difference two cells inward, which could leave the grid (`CovFitError` "outside the grid";
  found by WP13, where a three-node D0 grid of DRAGON2 runs with the truth in the upper cell could not be fitted).
  Steps are now cut at the grid edges: a three-point central difference with unequal steps inside the grid, and on
  an edge a one-sided step no longer than half the room left. Where a full cell fits on both sides the step is as
  before. New test `JacobianStepsStayInsideTheGrid` (four axes with the truth in an edge cell, uniform and
  non-uniform; the error on a parameter the model is linear in matches the 11-node fit within 2%) failed before the
  fix. Rerun of the WP13 three-node grid with the fix: D0 = 3.664e28 for a truth of 3.6e28 (|ln| = 0.018, error
  0.023), the same best fit as the five-node grid.
- New theory profile `theory:heliospheric-modulation` 0.1.0 (WP14): force-field solar modulation by reference to
  `skills/hep-measurement/scripts/solar_modulation_force_field.py`, which the profile runs as a separate process and
  does not reimplement (profiles may import only core and contracts). `scripts/derive.py` checks in SymPy that
  F(T + |Z| phi) solves the zero-streaming equation with a diffusion coefficient proportional to rigidity (the opposite
  sign does not), that T + |Z| phi is constant along the characteristic, the p^2 flux relation, the closed forms of a
  power-law local interstellar spectrum in total kinetic energy, kinetic energy per nucleon and rigidity, and their
  limits (`analytic-derivation`). `scripts/predict.py --benchmark` compares the script with those closed forms on 90
  synthetic points (two species, phi 0 to 1 GV, three energy kinds) to a relative 1e-10 (largest difference 2.4e-15),
  with phi = 0 and a demodulate round trip; `demonstrated-on-synthetic-data`, 25 profile tests. The validity range
  (breakdown below about 300 MeV/n for protons and 250 MeV/n for alpha particles) and the known limits (no rigidity-,
  time- or charge-sign-dependent effects; phi degenerate with the spectrum) cite Gleeson and Axford 1968, Ghelfi et al.
  2016 and Cholis et al. as read on 2026-10-13 for the hep-theory cosmic-ray reference. Convection-diffusion, drift and
  1D-3D numerical models and the neutron-monitor link are documented only, as unverified context; multi-period fits of
  phi point to `skills/hep-statistics/references/time-series-inference.md`. No source-term profiles (dark matter,
  pulsars). Registry: 2,264 of 3,072 bytes.
- `skills/hep-theory/references/cosmic-ray-propagation.md` no longer says the force-field script's rigidity and
  tabulated-spectrum inputs are planned (they shipped earlier), and names the new profile's role without its ID.
- `contracts/registry.py` rejects an unknown flag or a stray argument with exit 2 and a JSON error naming it
  (`{"ok": false, "error": "unknown option '--bogus' ..."}`). Before, an unknown flag such as validate.py's
  `--profiles-from` was ignored and the run reported `ok`, so a companion check with the wrong flag looked clean.
  `--registry`, `--local` (repeatable) and `--strict-versions` work as before; `--help` prints the usage.
- Test robustness: `test_tikz_error_is_a_source_error` (hep-communication diagram check) skips with the preflight's
  reason when a TeX engine is on PATH but the install fails the renderer preflight (for example a missing
  `luatex85.sty`, exit 3), as its no-TeX neighbour does; with a complete install it still asserts exit 1 and one
  source error. A stand-in engine covers the skip. No plugin code changed.
- `contracts/lineage.py decision` now compares each `artifacts[].sha256` with the file it names: relative refs resolve
  against the decision record's folder (or `--artifacts-root DIR`), absolute refs are used as they are. A different
  hash is `lineage.artifact_mismatch`, a missing file `lineage.artifact_missing`, an unreadable one
  `lineage.artifact_unreadable`, all errors (exit 1), as a missing exposure record is. `check_decision()` gains an
  optional `base_dir`; without it the library check is unchanged. No schema change. The hep-ml pre-training freeze
  example passes as shipped; a changed split manifest now fails `lineage.py` itself, and only the hash written in the
  `decision` text is still compared by hand (`ml-analysis.md`, capability matrix updated).
- Registry budget raised from 2,048 to 3,072 bytes (`REGISTRY_BUDGET` in `contracts/registry.py` and
  `registry_bytes` in `tools/measure_entrypoints.py`; decision D3 of the WP13–WP16 order). The registry was at 2,001
  bytes with 8 entries, and one more theory profile costs about 163 bytes plus its scope, so no further profile fit.
  The registry is read only when a profile is needed, so this does not change the always-on description cost. The
  tests now take the budget from `contracts/registry.py`, and a new test checks that the two constants agree.
- Routing: hep-computing's description says to load it first even for a quick build or code fix (`co-companion-ws-1`,
  a CMake fix in a project that binds a companion profile, now loads hep-computing in 3/3 live runs, was 1/3), and
  hep-communication's description says to ask first when a comparison names no observable or experiments (it was
  shortened to stay under 1024 characters; every trigger phrase the routing cases rely on is kept). The routing case
  `rc-t3-neg` ("is this Feynman diagram allowed at tree level?") now has a synthetic `diagram.tex` (a three-photon
  vertex) as its input: without it the model rightly asked for the diagram; with it hep-theory loads in 3/3 runs.
  `wp11-xexp-3` (an underspecified flux comparison) still loads hep-communication before asking, so the harness still
  counts it as a miss, but the model now asks for the observable and experiments straight away in 3/3 runs instead of
  exploring the tree until it ran out of turns (2/3 before). Live check on the 72 cases that involve either skill or
  ask for a question: 69/72, with the other two misses (`eic-underspec-1`, `t19-turns-3`) the same as in the
  2026-10-08 baseline.
- Test robustness: `test_scaling_check_rejects_a_quadratic_scan` (hep-communication manuscript scan) models the
  quadratic rescan as a Python loop over the earlier lines instead of `str.count` over the earlier text. On a CI runner
  the `str.count` byte rate grew with the text, giving a ratio of 7.4 instead of about 16 and a spurious failure (PR
  #108, job `optional (root-uproot)`; passed on rerun); the loop's cost per step is interpreter work, so the ratio
  stays near 16 (14.5–16.6 in five repeats each on an idle and on a loaded laptop). No plugin code changed.

## 0.11.0 (2026-10-15)

AMS-02 skill upgrade (work order WP1–WP12, WP15), four skills renamed, Python 3.13 as the minimum, and CI
improvements. **Contracts 2.9.0** (skill-name aliases). **Breaking for users:** the skills `hep-analysis`,
`detector-response`, `research-communication` and `physics-ml` are now `hep-measurement`, `hep-detector`,
`hep-communication` and `hep-ml` (old names in artifacts and profiles are accepted with a deprecation warning, an error
under `--strict-versions`; `contracts/migrate_skill_names.py` rewrites them), and Python 3.11 and 3.12 are no longer
supported. The companion ams02-research 1.5.0 follows the rename (it requires hep-research >=0.11.0).

- Skill READMEs brought up to date with the tree (no SKILL.md or capability change): hep-computing counts 32
  references and 13 test modules (PyROOT floor test), and `find_python.py` is described with its Python 3.13 floor;
  hep-statistics counts 20 test modules and names the `tabulated-grid` status (demonstrated on synthetic data), its
  exit 3 for a missing covariance or correlation, and `examples/bc-propagation-fit`; hep-theory lists the
  `bc-propagation-fit` example, the 3.13 interpreter floor and its out-of-v1 domains; hep-measurement counts its 12
  references and 21 test modules, lists all its assets and the link to the hep-statistics time-series reference;
  hep-detector states the charge-confusion note's `documented` status; hep-communication points at the behavioral
  evaluation's real folder (`evals/research_communication/`) and its two recorded live runs. The four renamed skills'
  READMEs say in one line which old name is a deprecated alias (contracts 2.9.0).
- `docs/reference-inventory.{json,md}` regenerated (the hep-measurement README now cites `time-series-inference.md`).

- `theory:cr-secondary-antiprotons`: external benchmark for open question B2. `scripts/published_benchmark.py`
  recomputes the pp-induced source term of di Mauro, Donato, Goudelis and Serpico, PRD 90 (2014) 085017
  (arXiv:1408.0288v3), Table VI, from the same paper's closed-form parametrizations (Eqs. (11)-(13), (B1)-(B2);
  Tables III-V, VII; `models/xs-dimauro2014-pp.json`, benchmark use only) and the proton flux of arXiv:1402.0321v2
  Sec. 2.3. Tolerance per entry is the paper's own Table VI error: 12 of 15 entries reproduced (within 2.5% at 5 and
  10 GeV); Eq. (11) at 1000 GeV and Eq. (13) at 500 and 1000 GeV (unstated projectile-energy upper limit), plus the
  spline, Tan & Ng and Duperray et al. columns, documented as not reproduced
  (`benchmarks/published-source-term-dimauro2014.json`). New capability `source-term-external-benchmark`
  (tested-in-declared-environment, E2); 12 new tests (48 in the profile).
- `theory:cr-secondary-antiprotons` evidence: di Mauro et al. 2014 read in full (title corrected), Korsmeier et al.
  2018 and Winkler 2017 opened for tables and ancillary files (no tabulated source term), new source `crpb:S05`
  (arXiv:1402.0321v2) and claims `crpb:C07`-`C11`.
- `theory:cr-secondary-ratio`: open question B1 stays open. Five papers examined on 2026-10-15 tabulate fit
  parameters or cross sections and show B/C in figures only; search record
  `benchmarks/external-benchmark-search.json`, absence claim `crsr:C06`, read levels updated, 4 new tests.
- `docs/capability-matrix.md` Profiles rows and `VALIDATION.md` (CR-BENCHMARKS-B1-B2) updated.

- `find_python.py`: `--min-python` bad usage is decided in `main()` before `find()` runs, so only the format and floor checks exit 2 and any other `ValueError` from `find()` propagates; the CLI error names `--min-python` (not `min_python`); `--min-python` must be dotted non-negative integers (`^[0-9]+(\.[0-9]+)*$`), so `3.13.-5`, `3_14`, `+3.14` and padded values are refused.
- `tools/run_all_checks.py` and `tools/check_ams_optional.py` stop at once with exit 2 and "Python 3.13 or newer is required (running X.Y)" on an older interpreter, instead of running into version-dependent test failures.
- CI: the weekly `latest` job (slow tier) sets `HEP_MODULE_TIMEOUT=1800`: `tests.examples.test_stats_benchmarks` takes about 525-545 s alone there, near the default 600 s limit (toys, seeds and tolerances unchanged); documented in `docs/maintenance.md`.

- `test_scan_time_is_linear_in_lines` measures CPU time (minimum of three, garbage collector off) and bounds the 10k -> 40k line scaling ratio (limit 10; linear about 4, quadratic about 16) with a generous absolute ceiling; it no longer fails on a loaded machine, and a synthetic quadratic scan is shown to fail the same check.
- New `tests/tools/test_python_compat.py`: `core/partition/runner.py`, `find_python.py` and the two suite runners parse as Python 3.9, the `PROBE` string as 3.7 (`ast.parse` feature_version plus PEP 701 f-string, starred-subscript and `datetime.UTC` checks); a real old interpreter compiles them when present.
- The old-floor check now covers `docs/deployment-model.md` and the current statements of `docs/capability-matrix.md`; the matrix's dated E1/E3 environment lines, floor note and E3 ROOT row are excluded by name and must still exist.
- `test_stricter_minimum_is_kept` checks the rejection reason with a fake 3.13 interpreter on any runner (it asserted nothing on 3.14+).
- Long lines wrapped in `find_python.py` and the floor tests; the `test_broken_power_law` tolerance comment describes 3.11 as history.

- Routing: hep-communication's "Not for" clause says "even with published data" and names CRDB queries (hep-theory) and compatibility results (hep-statistics), so requests that name experiments but ask for a result go to the owner; live (2026-10-15): `wp11-crdb-1` 3/3, `wp11-xexp-2` 2/3 (both 0/1 before), all 25 hep-communication cases still pass; `wp11-bound-dm-1` (dark-matter interpretation) also accepts hep-communication. Known misses: `wp11-xexp-3` (underspecified comparison loads hep-communication instead of asking), `rc-t3-neg`, `co-companion-ws-1` (no skill).

- **Four skills renamed** (rename release 0.11.0; contracts 2.9.0). Skill folders, `SKILL.md` `name` fields, test
  folders (`tests/skills/<underscored>`), descriptions' "Not for" lists, handoff tables, READMEs, profiles'
  `related_skills`, the capability matrix, routing cases and docs use the new names:

  | Old name | New name | Test folder |
  | --- | --- | --- |
  | `hep-analysis` | `hep-measurement` | `tests/skills/hep_measurement` |
  | `detector-response` | `hep-detector` | `tests/skills/hep_detector` |
  | `research-communication` | `hep-communication` | `tests/skills/hep_communication` |
  | `physics-ml` | `hep-ml` | `tests/skills/hep_ml` |

  `hep-statistics`, `hep-theory` and `hep-computing` are unchanged. Files named after a skill follow the same rule:
  `references/hep-measurement-guide.md` (was `hep-analysis-guide.md`), `assets/diagrams/hep-measurement-pipeline.md`,
  `tests/skills/hep_detector/test_hep_detector_audit.py`, `tests/skills/hep_ml/test_hep_ml_skill.py`. Release
  manifests, past CHANGELOG entries, dated VALIDATION.md sections and past eval results keep the old names.
- **Contracts 2.9.0: deprecated skill-name aliases.** `contracts/schemas/skill_names.json` (referenced by
  `envelope.json` `provenance.producer_skill` and `profile.json` `related_skills`) and `contracts/skill_names.py`
  accept the seven names plus the four old names as deprecated aliases. An old name in `provenance.producer_skill`,
  `handoff.to_skill` or an extension `handoff` is the warning `skill.deprecated_name`; in a profile's
  `related_skills`, `profile.deprecated_skill_name`. Under the version and name policy (`--strict-versions` of
  `contracts/validate.py`, `contracts/dependencies.py` and, new, `contracts/registry.py`; and protected use) each is
  an error. A 2.8 reader rejects a new name (schema enum) instead of misreading it; no capability is added. The
  aliases are removed one or two releases later.
- **`contracts/migrate_skill_names.py OLD.json [--out NEW.json]`** rewrites `provenance.producer_skill` and
  `handoff.to_skill` to the new names and nothing else (not `contract_version`, not the extension); remaining
  findings are reported, never repaired. Exit 0 migrated or unchanged, 2 unreadable or not an object. Fixture
  `contracts/fixtures/skill_aliases/response_old_skill_names.json`; tests
  `tests/contracts/test_skill_name_aliases.py` (old name warns, fails under `--strict-versions`, validates cleanly
  after migration; registry warning and strict error for `related_skills`).
- Contract fixtures, example outputs (contracts version and producer names) and the gate-verdict snapshot
  regenerated; `docs/maintenance.md` documents the name policy. ams02-research 1.5.0 requires `hep-research
  >=0.11.0` and names the new skills in its profile.

- **Python 3.13 is the minimum** (validation-first migration; Gate 1 evidence in VALIDATION PY313-FLOOR): `requires-python = ">=3.13"`, Ruff `py313`, mypy `3.13`; `skills/hep-computing/scripts/find_python.py` selects only Python 3.13 or newer (default and lowest allowed `--min-python` 3.13: a lower value is bad usage, exit 2; `find()` raises `ValueError`), with 3.11/3.12 rejection, fallback and all-old tests. CI's checks matrix runs on Python 3.13 only (4 jobs instead of 12; the backend jobs already ran on 3.13 and are unchanged), and `checks-complete` reconciles 3.13 only. **Migration:** Python 3.11 and 3.12 are no longer supported or tested; create the environment with Python 3.13 (`python3.13 -m venv ...`, then `pip install -r requirements-core.txt`) and point `HEP_RESEARCH_PYTHON` at it. Scripts run directly are not stopped by `requires-python`; the skills choose the interpreter with `find_python.py`. Python 3.14 is installable but not tested. Dependency pins are unchanged (the 3.11-era upper bounds in `requirements-ci-constraints.txt` stay until a separate dependency change).
- Capability statements for cosmic-ray propagation rewritten to the achieved status (WP10): guidance, the two narrow theory-domain profiles, the `tabulated-grid` fit and `examples/bc-propagation-fit` are demonstrated on synthetic data; only global fits that run a propagation code stay outside v1 (capability matrix, `cosmic-ray-propagation.md`, hep-theory README). The hep-statistics description's out-of-v1 example is now "global propagation fits" (1,016 characters) and the shared context-resolution stanza says "global cosmic-ray propagation fits" in all seven SKILL.md files; the four WP11 propagation-fit routing cases are direct cases now (static routing passes).

- Profile `theory:cr-secondary-antiprotons` 0.1.0: the secondary antiproton source term q(T_pbar) for the channels
  pp, pHe, Hep and HeHe with the antineutron and hyperon factor (2 + Delta_IS + 2 Delta_Lambda), following the
  hep-theory cosmic-ray reference conventions. TOY x-scaling cross sections with ILLUSTRATIVE values (no published
  parametrization reproduced); the closed-form source integral (incomplete beta functions, checked in SymPy) is the
  internal benchmark of the numerical quadrature (agreement 3e-15, criterion 1e-8). `model.family` is
  `cosmic-ray-secondary-source-term`, so `theory.degeneracy_missing` does not apply. 36 profile tests, capabilities at
  `demonstrated-on-synthetic-data`. Published source-term values as a benchmark remain open (B2). Registry 2,001 bytes.
- Example `examples/bc-propagation-fit/`: a 21 x 21 log-spaced (D0, L) grid of `theory:cr-secondary-ratio`
  predictions (882 gated artifacts, two illustrative cross-section sets), SYNTHETIC B/C points with a full covariance,
  and `covariance_fit.py` `tabulated-grid`: D0/L recovered (Asimov within 0.25 sigma, pseudo-data pull -0.41, 100 toys
  with pull mean 0.02 and width 0.95), D0 and L unconstrained, one degenerate direction along (1, 1) matched to the
  theory spec's `D0/L`, cross sections as a model set; ungated, rigidity-binned, unfolded-level and
  unknown-correlation inputs refused. Test `tests/examples/test_bc_propagation_fit.py`.

- `adapters/crdb` 0.1.0 (owner hep-theory, optional, `tested-in-declared-environment` on E2 with CRDB V4.2): one query of the CRDB (LPSC) REST interface, promoted from the ams-02 profile's `scripts/crdb_query.py`. No default experiment filter (`url`/`fetch` without `--exp-dates` or `--all-experiments` exit 2); every summarized row and sub-experiment group carries `secondary: true`; the `.meta.json` sidecar holds the request (parameters, URL, User-Agent), UTC retrieval time, CRDB version, export date and the SHA-256 of the saved file. HEPData or the paper's tables are primary; a CRDB value is a cross-check or a fallback labelled secondary. Offline tests replay four CRDB exports recorded live on 2026-10-15 (`tests/adapters/test_crdb_query.py`, VALIDATION CRDB-ADAPTER).

- ams-02 profile: `scripts/crdb_query.py` and `tests/test_crdb_query.py` removed; the profile lists `adapter:crdb` as optional and its cross-check step passes `--exp-dates AMS` explicitly; capability `papers-manifest-and-crdb-query` renamed `papers-manifest`. `cosmic-ray-databases.md` records that `exp_dates=AMS` also returned an AMS01 row (2026-10-15). Rules and claims C125-C129 unchanged.

# WP3 changelog bullets (for "Unreleased")

- Profile `theory:cr-secondary-ratio` 0.1.0, the first narrow cosmic-ray propagation domain: B/C (from C and O) in a
  weighted-slab (leaky-box) model and a 1D thin-disc diffusion model without convection. SymPy checks of the closed
  forms, of their equivalence through lambda_esc = n_H m_H h v L / D and of the resulting D0/L invariance
  (`scripts/derive.py`); a benchmark of the closed forms against the profile's own numerical solutions (slab ODEs
  averaged over the path-length distribution, a finite-thickness disc solved exactly and by finite volumes, and its
  thin-disc limit; `scripts/predict.py --benchmark`); a theory-spec artifact with `model.family`
  `cosmic-ray-propagation` and `degenerate_directions: ["D0/L"]`; a bin-averaged prediction artifact with a
  cross-section model alternative; and a prediction callable at any parameter point and on (D0, L) grids
  (`predict.evaluate`, `predict.grid`, `predict.bin_averaged`, CLI `--set` / `--grid`) for the grid fit of WP1/WP8.
  Cross sections and transport values are ILLUSTRATIVE; references are cited but were not opened (no network).
  Status `demonstrated-on-synthetic-data`, 37 profile tests, including one showing that a theory-spec without
  `degenerate_directions` fails `contracts/validate.py` with `theory.degeneracy_missing`.
- Capability matrix: a "Profiles" row for `theory:cr-secondary-ratio`.

- `examples/eic-profile-routing/output/` regenerated: the run lists every registered `profile.json` it opens, which now
  includes the new profile.

- CI: a new commit on a pull request cancels that PR's superseded `tests` run (pushes to main, the weekly and manual runs are never cancelled); pip downloads are cached by `setup-python`, keyed on `requirements-ci.lock` (installs and tests still run in full every time). Batch 2 (low-risk part) of the CI improvement proposal.

- hep-statistics: `covariance_fit.py fit` model `tabulated-grid`: fits grid parameters (for example D0 and L) to a
  `dataset-record` from one `prediction` artifact per grid node (`representation: "grid"`, node in `parameter_point`;
  no schema change). Every prediction passes `contracts/comparison/gate.py` first (ungated or not comparable: exit 1);
  multilinear interpolation in the fit coordinates (`scale: "log"` or `"linear"`), no extrapolation (a start outside
  the grid or a minimum beyond its edge is refused); cross-section uncertainty as a rank-one normalization nuisance
  (`multiplicative`, mode `nuisance`) and/or alternative sets through `model_set()` and `envelope()`, the mode recorded
  in `cross_section_uncertainty.mode`; degenerate directions from the Fisher matrix reported with eigenvector and
  condition number and compared with the theory spec's `degenerate_directions` (mismatch: warning); `combinations`
  such as `D0/L` reported with `sigma_ln`. Tests: `tests/skills/hep_statistics/test_grid_fit.py` (synthetic only).
  Status: demonstrated on synthetic data (E2, 2026-10-15).
- `covariance_fit.py`: exit code 3 (`"status": "incomplete"`, `missing`) when a data covariance or an uncertainty
  correlation is missing; a diagonal matrix is never assumed.

- `covariance_fit.py`: a field of the wrong JSON type now gives exit 2 with a JSON error instead of a traceback.

- CI (batch 1 of the CI improvement proposal, test obligations unchanged): `tools/run_all_checks.py` records seconds for every check, prints failed test ids with their traceback tails (profile suites and `check_ams_optional` included) and writes a Markdown job summary with `--summary FILE`; `--part static` and `--part ams-optional` split `--part checks` so the AMS-optionality check (about 75 % of the old "static and profiles" job) runs as its own CI job. Each units run records its plan (full module list with SHA-256, the shard's modules, the timings digest).
- CI: new `tools/reconcile_check_runs.py` and required-in-practice `checks-complete` job: every expected checks run (Python 3.11-3.13 × units 1/2, 2/2, static, ams-optional) present once, of the tested commit, passing, with only the host CLI checks skipped, every planned check reported, and the shards partitioning this tree's module list (planned from the same timings); runs after failures (`always()`), and a missing record fails it. Fault-injection tests in `tests/tools/test_reconcile_check_runs.py`. Its first local run caught shards planned from two different timing files (a module in two shards, others in none) at equal test counts.
- `tools/module_timings.json` refreshed from GitHub Actions run 38680162693 (median of the 6 units-shard samples per module; 53 modules had no record, `test_stats_statistical_toys` was recorded at 70 s and now takes 177 s): the planned 2-shard split of the measured time goes from 1028 s / 845 s to 937 s / 937 s.

- `adapters/literature-lookup` 0.1.0 (optional, owned by hep-communication, standard library only): `literature_lookup.py` looks up an arXiv id (with or without version), DOI, INSPIRE record id or ADS bibcode in INSPIRE-HEP, arXiv and ADS and prints one record per source with source URL, UTC retrieval time, read level and an arXiv version check; HTTP 429 reported as `rate-limited` and never retried; ADS token from `ADS_API_TOKEN`/`ADS_TOKEN`, never printed or recorded, `not-verified` without it; `--replay`/`--record` for recorded responses. Exit 0 found, 1 not found, 2 bad input, 3 incomplete. Status `demonstrated-on-synthetic-data` (INSPIRE-HEP and arXiv `tested-in-declared-environment`, ADS on a constructed response only).
- `tests/adapters/test_literature_lookup.py` with fixtures recorded from INSPIRE-HEP and arXiv on 2026-10-15 (found, not found, HTTP 404, a real arXiv HTTP 429, version mismatch) and constructed INSPIRE 429 and ADS responses; offline (urlopen patched to fail); live smoke only with `HEP_LIVE_LOOKUP_TEST=1`.

- Capability matrix: "Literature and citation verification online" raised from `unverified` to `tested-in-declared-environment` for INSPIRE-HEP and arXiv (E2, live 2026-10-15), ADS `demonstrated-on-synthetic-data`; new Adapters row. VALIDATION LITERATURE-LOOKUP.
- `literature-lookup-recipes.md`: optional lookup-client section; arXiv answered HTTP 429 to a nonexistent id (observed 2026-10-15). hep-communication README and `docs/adapter-authoring.md` (network declaration) updated.

- Routing: 27 new cases (set `WP11`, 13 en / 14 zh-Hant) in `tests/routing/make_cases.py` for cosmic-ray interpretation, propagation fits (hep-statistics, limited support until WP10), time-series inference, cross-experiment comparison, CRDB queries, a custom e/p classifier in a measurement (hep-ml, handoff to hep-measurement), and the dark-matter-interpretation (hep-theory, limited support) and latest-B/C-paper (hep-communication) boundaries; `cases.json` regenerated (241 cases). The live harness in `evals/routing/` reads the same `cases.json`, so it picks them up unchanged.

- `skills/hep-statistics/references/time-series-inference.md` (documented): inference on **binned** time series:
  time-bin covariance as statistical + fully correlated time-independent + time-dependent blocks (valid exponential or
  epoch correlations, positive-definiteness, correlation-time limits, no averaging down, cancellation in ratios,
  rigidity x time Kronecker structure, Peelle); periodicity against an AR(1) red-noise null fitted with the measurement
  covariance and why Rayleigh/Z_m^2 (event-level, white noise) do not apply; trials across periods and energy bins by
  toys of the complete procedure (pattern of `look_elsewhere.py` and `global_significance.py`, which are not periodogram
  tools; the shipped Gross-Vitells bound is one degree of freedom); joint multi-period fits with one modulation
  parameter per period, shared parameters and nuisances for time-independent sources via `covariance_fit.py` plug-in.
  Linked from `SKILL.md` Resources, the core-stats-guide reference index and `astroparticle-statistics.md`.
- `tests/skills/hep_statistics/test_time_series_covariance.py`: the covariance recipe on a synthetic series
  (demonstrated-on-synthetic-data); a nearest-neighbour correlation of 0.7 is refused by `validate_covariance.py` as
  not PSD.

- hep-measurement: `references/cosmic-ray-measurements.md`, an index of cosmic-ray measurement types (absolute flux, flux ratios, isotope ratios, time-dependent flux, rare-event searches) that links existing sections in hep-measurement, hep-detector, hep-statistics and hep-communication, plus new anisotropy measurement design: estimand (first harmonic, equatorial dipole projection, 3D dipole), directional exposure and its non-uniformity (simulated vs data-driven, east-west method), harmonic and full-sky dipole estimators, partial-sky multipole coupling, amplitude bias, solar/sidereal/anti-sidereal checks, and upper limits on the amplitude with the limit construction handed to hep-statistics (Linsley 1975, Sommers 2001, Billoir & Deligny 2008, Ahlers & Mertsch 2017, Compton & Getting 1935, Farley & Storey 1954, Alexandreas et al. 1993, Bonino et al. 2011). Linked from `SKILL.md` Resources and the analysis guide's routing table; capability matrix row `documented`.

- hep-detector: `references/charge-confusion.md`, a synthesis note on charge-sign confusion: the mechanisms (finite curvature resolution toward the maximum detectable rigidity, non-Gaussian scattering and interactions, wrong hit association; alignment weak modes making the two signs' rates differ), how hep-detector measures the rate (simulation validated on data, templates in a confusion-sensitive variable, known-sign control samples) and the handoff to hep-measurement, which subtracts it as a background; linked from the principles-summary reference index and task-routing table and from the tracking reference. Capability-matrix row at `documented` (WP15).

- hep-ml: pre-training freeze procedure in `references/ml-analysis.md` ("Training on data and blinding"): before training, a `decision_record` (category `other`) states labels, features, training domain and the split manifest's file SHA-256, lists the manifest in `artifacts`, and binds `seen` to the analysis's exposure record; checked with `contracts/lineage.py decision`, plus a manual file-hash comparison since `lineage.py` does not open artifacts (WP7).
- hep-ml: synthetic example `assets/pretraining-decision.example.json` with `pretraining-exposure.example.json` and `pretraining-split.example.json`; `tests/skills/hep_ml/test_pretraining_freeze.py` checks it (lineage exit 0, exposure at decision `unexposed`) and shows that an edited exposure history, an understated `seen`, a decision dated before what it counts, a changed split manifest and a hash that disagrees between `artifacts` and the text fail (WP7).

- WP6: hep-communication quick-question routing re-measured live on 0.10.1 (routing 29/31, hep-communication 20/20; communication eval 5 of 11 cases still answered without a skill, a description-level decision); `SKILL.md` unchanged; recorded in VALIDATION (WP6-QUICK-ROUTING) and capability matrix.

## 0.10.1 (2026-10-15)

Follow-ups to the 0.10.0 check (PR #84) and the `run_all_checks.py` timeout fix (PR #83). ams02-research needs no
change (it requires hep-research >=0.4.0 and contracts >=2.0). Contracts stay 2.8.0.

- `tools/run_all_checks.py`: a check script that does not finish within the timeout (`--module-timeout`, default 600 s,
  now applied to the check scripts as well as the test modules) is a failure with the reason "timed out after N s";
  the remaining checks still run. Before, the uncaught timeout aborted the whole run with a traceback (seen in the
  0.10.0 release gate when two runs shared the CPU and `ams_optional` passed 600 s).

Follow-ups to the check of the three audit orders on 0.10.0 (every rerun item verified, no regressions; the open
items below were fixed, sources opened 2026-10-15).

- detector-response: tool contract for `frontend_response.py` (`contracts/tool_contracts/frontend_response.json`, ten
  operations checked against each subcommand's `--help`; exits 1 and 2 print JSON); its top-level usage is one line so
  the checker sees every subcommand. Tests: `FrontendResponseContractTests`.
- detector-response references, from PDG RPP 2025 reviews 34-36, NIST PSTAR, the Geant4 manuals and the arXiv papers
  named in the text: noble-liquid W values and pulse shapes; Gluckstern validity (N >= 10) and the `beta` power of the
  scattering term (PDG eq. 35.70, unchanged); silicon response; Lindhard quenching; transition radiation; stopping-power
  corrections; Polya gain; resistive induction; SiPM and APD noise; LGAD timing (15-20 ps); compensation and
  containment; Geant4 production cuts; prescale handling; luminosity uncertainty; tracker weak modes; Hillas
  parameters; CTAO LST status; neutrino telescopes; new notes on muon detectors, radio detection and wide-field
  gamma-ray arrays (HAWC, LHAASO-KM2A); a `Check:` line per section in the triggers, physics-objects and
  event-reconstruction references. Rows still without an openable source stay deferred in VALIDATION.
- hep-analysis `geomagnetic_cutoff.py`: the default dipole moment 8.05e25 G cm^3 is stated once as the IGRF-14 1955
  dipole (C = 59.6 GV); the 2025 dipole is 7.69e25 G cm^3 (cutoffs about 4.5% lower). Default and outputs unchanged.
  Test: `GeomagneticDipoleDefaultTests`.
- Contracts: committed fixtures for the 2.8.0 ml-artifact rules (53 files, `ml_v28_*`, `statres_v28_*`) and a test
  that every 2.8.0 ML code has one; `gate_verdicts.json` gains rows, no verdict changed. No contract version change.
- physics-ml: regression tests for `anomaly_validation`, `reweighting_validation` and the temperature-at-bound warning.
- research-communication: the Springer Nature AI-use row states what the public policy page says (an "AI Declaration"
  in the manuscript, disclosure in captions for AI visuals; AI not an author); the ADS `citations()`/`references()`
  operators are stated from the ADS help source instead of marked unverified.
- VALIDATION: detector-response deferred list updated (and the work order's "FWHM" 6271594.24 is the falling
  half-maximum depth; FWHM is 2358463.01); physics-ml references size 179,135 B.

## 0.10.0 (2026-10-14)

The detector-response, physics-ml and research-communication audits (PR #81). ams02-research needs no change
(it requires hep-research >=0.4.0 and contracts >=2.0).

Contracts 2.8.0 (minor: new rule families refuse false or incomplete declarations; new fields optional; no new
capability; artifacts before 2.8.0 keep their default outcome and get the new rules under `--strict` and at the gate).
Research-communication adds one value to 2.8.0: `reporting_context.result_type` accepts `flux-measurement`
(`ext_communication_traceability.json`; add-only, RC-C3).

### research-communication (RC-AUDIT-2)

- **A displayed number that disagrees with its passage fails (RC-A2, sci-fix).** `check_communication` and
  `audit_claims` compared a declared display value with its passage as a substring warning, so `1.0` passed inside
  `1.02` and a record of 1.09 against a manuscript of 1.02 exited 0. One number tokenizer
  (`communication_lib/numbers.py`: sign, exponent, grouping, `\pm`/`±`, LaTeX and Unicode forms, CJK adjacency)
  now compares numbers as `Decimal`; absence is the error `occurrence.value_not_in_passage`.
- **Adaptation drafts read numbers at a sentence end and next to Chinese text (RC-A3, sci-fix).** A 9.99 draft
  against a 1.02 record passed `check_adaptation` in English (full stop) and Traditional Chinese.
- **Every display is checked against its source (RC-A5, RC-A15, sci-fix).** Without a rounding rule a display that
  is no rounding of the source is `occurrence.value_mismatch` (it was a warning); a malformed rule, NaN or infinity
  is a record finding (exit 1), not an input error.
- **Rounding rules round half up (RC-A6, sci-fix).** `decimals:2` turns 1.025 into 1.03; `:half-even` keeps the old
  mode. Skill library only; no contracts change. The worked example's audit report shows policy version 1.1.0.
- **`check_manuscript.py` reads LaTeX and BibTeX as TeX does (RC-A1, A4, A7, A9, A18).** Brace-less `\input name`
  is followed; `\Citet`/`\Cite`, multicite groups, nested optional arguments, `%` inside `\url`, entries inside
  `.bib` fields or `@comment`, `\iffalse`, the comment environment, `\verb` and crossref parents are handled; a
  `--bbl` outside the project root is an input error; scans are linear (20,000 lines: 10 s to under 0.2 s);
  `--strict` unused entries are unresolved while coverage is incomplete.
- **Locators and normalisation (RC-A8).** Section titles with nested braces, `\pm`/`±`/math shifts/ties on both
  sides, no headings inside fenced code.
- **Traditional Chinese parity (RC-A10, A13, A17).** Status-promotion, discovery, scope, negation and attribution
  scans, symbol and abbreviation definitions work in Traditional Chinese; status labels match as words; a
  disallowed term inside a declared term is not flagged; an abbreviation used before its definition on the same
  line is.
- **`check_diagram_sources.py` compiles TikZ (RC-A11).** LuaLaTeX (else pdfLaTeX), standalone harness with
  tikz-feynman and the file's setup fences, `--no-tikz`, a skip directive for fragments; a named file without a
  block exits 2. The bundle test compiles TikZ only under `HEP_SLOW_TESTS=1`.
- **Smaller checker fixes (RC-A12, A14, A16, A19).** Revision impact flags empty records and unmapped added claims;
  `--today notadate` and an output aliasing the input are refused; the README says which tool prints what.
- **Text facts (RC-B1-B13).** SKILL.md quotes the read-level vocabulary and names `user-supplied`; one rule for
  values read off plots; deduplication on DOI, arXiv id, INSPIRE record id; correction labels follow the venue;
  PRL Comment length from the APS page; dated AMS-02 specifics removed from references (one sourced absence claim,
  `ams02:C185`, added to the public profile ledger instead); diagram logic (result from the fit, vertex checks,
  pileup stage); compile records and the LuaTeX warning; smaller wording fixes.
- **Usability (RC-D1-D7).** A quick-questions block in SKILL.md and a trigger-first description (978 characters): the
  quick literature questions and citations come first, with the instruction to load the skill even for a quick
  question; every trigger phrase the routing cases use is kept (SKILL.md 8126 B). One home per rule (significance and limit wording, venue facts, posters and talks, captions,
  colour and raster); the papers guide cut to routing, rules and pointers; executable checks instead of
  "mentally desaturate"; a "Done when" line in every reference; reference link test.
- **New content (RC-C1-C11).** `physics-plots.md` (status labels on figures, ratio panels, `pdf.fonttype = 42`,
  colour and raster, cosmic-ray flux and neutrino figures), examples `hep/09`-`hep/11`, limit and null wording,
  the `flux-measurement` reporting policy, `collaboration-results-lifecycle.md`, AI-use disclosure raised
  unprompted with a dated venue table, HEPData records, `literature-lookup-recipes.md` (INSPIRE, ADS, arXiv),
  NSTC/ERC/JSPS and bilingual proposal rules, retraction and SCOAP3 licence checks, combination papers, poster and
  talk formats.
- **Records (RC-E1, E3).** The capability matrix records the live run of 2026-10-13 and where the evaluation files
  live; reference counts updated.

### physics-ml audit (ML-…)

Scientific corrections first (`sci-fix` commits; each with a regression test that failed on 84202aa).

- **Split tools check what they claim (ML-C02, C03, C04, C05, C14, C16, C28).** `check_split_integrity.py` refuses
  (exit 2) a timestamp that is not a finite number or an ISO-8601 date (NaN, `2024-1-10`), a `temporal_order` naming a
  split the file does not have or fewer than two, booleans, lists or objects as keys, and a misspelled reserved key;
  an empty split is `incomplete` under `--strict`; `timestamps_checked` is true only when the comparison ran. One key
  function for both split tools: 1, 1.0, "1" are one group. `make_grouped_splits.py --mode temporal` no longer sorts
  dates as text; `--label-column` reports class counts and refuses a split without a class. `train_classifier.py`
  matches case-folded manifests and reports a split without a class as exit 2.
- **A calibration evaluated on its fit sample never validates (ML-C01, K03, C13).** `calibration.py` records both
  sha256 values inside the calibration block and needs `--id-col` (or `--no-id-check`, recorded); from 2.8.0
  `disjoint: false`, equal hashes or names equal after normalization are `ml.calibration_on_fit_sample`.
- **Domain-shift outcome (ML-K05).** `domain_shift.outcome` (no-shift, corrected, bounded-by-nuisance, uncorrected) and
  `nuisance`; a missing status or outcome, an uncorrected shift without a nuisance and a control sample equal to the
  training sample are unresolved. J9 carries its measured pt_miss scale as the fit nuisance `theta_pt_miss_scale`:
  mu 1.30738 +0.280857/-0.260727 -> 1.33104 +0.293293/-0.277051, toy coverage 0.693 -> 0.660 (criterion 0.635-0.73).
- **One training-domain method (ML-C08, C09, C19, C18).** `check_surrogate_domain.py`'s method is the importable
  `DomainModel` (grouped held-out calibration, categorical features, Clopper-Pearson interval on the false-positive
  rate); `train_classifier.py` stores it fitted on train only and `inference.py` applies it (a broken linear
  constraint is flagged, the per-feature range is a diagnostic, non-finite rows get no score, `--calibration`).
- **Negative weights are never dropped; the metric layer flags or refuses (ML-R06, C11, C12, C15, C20, C21, C22).**
  `--negative-weights {signed, abs, resample}` (cell resampling, Andersen & Maier, arXiv:2109.07851, eq. 2.2);
  signed-weight values outside [0, 1] are flagged, fractional labels refused, `asimov_significance` refuses bad
  sigma_b and keeps its precision at s/b < 1e-6, `undo_prior_shift` refuses r <= 0, temperature-scaling warnings,
  `disco_penalty(check_weights=True)` by default.
- **Physics references (ML-R01-R05, R12, R13, R17, R21, R25; WP2.2/2.3).** Regression prior dependence and the in-situ
  scale and resolution systematic; when an ML uncertainty is a measurement systematic; Platt, isotonic, prior
  correction, conformal; blinding when training on data; validating inputs before training; negative weights by
  library; OmniFold unmatched events and prior dependence; ANODE; flows and flow matching; two-sample tests with power;
  SBI sharpness and overconfidence; GNN tracking; label noise from truth matching; four contradictions resolved.
  Sources opened on 2026-10-14 or marked `unverified`.
- **Small corrections (ML-C10, C24, C25, C26, K13).** `compare_model_runs.py` decides with a Student-t interval below
  10 seeds (false-improvement rate about 5%, was 26%/15%/11% at 3/5/10 seeds); the sculpting baseline is a quantile of
  20 resamplings; a constant training feature is exit 2; `model_hash` covers the weights only; the J9 test compares
  the committed artifacts within a relative 1e-7 (the calibration fit differs by 2-6e-9 between Linux and macOS BLAS;
  digests over float bytes are skipped). Check runs now keep the traceback tail of each failing test.

Contract and tooling:

- **ml-artifact semantics v2 (ML_SEMANTICS_V2_FROM = 2.8.0; ML-K02, K04, K07-K12, K14, K16).** Structured
  downstream validation (vocabulary `ml_downstream_metrics`; ML-only or bare-pass lists are errors; `passed` must
  agree with a numeric value and criterion); `output_semantics` required for classification, inference and
  regression (unresolved); misspelled keys are errors (`_key_checks` takes a `kind`); task blocks
  (`regression_validation`, `generative_validation`, `sbi_validation`, `extrapolation_policy`,
  `reweighting_validation`, `anomaly_validation`; new task `reweighting`; `parameters` and `supervision`); training
  domain coverage, `model_hash` format, label/feature/preprocessing/threshold/unit checks; `observed` and
  `validated-in-scope` need support; structured weights with `training` and `evaluation`; calibration outcomes.
  The Appendix B mutation probe (`tests/contracts/test_ml_mutation_probe.py`) goes from 50 of 53 rows silent on
  84202aa to 1 (M47, by design).
- **ML provenance at the publication gate (ML-K01, K06).** Optional `extension.observable_source` in the
  statistical-result schema (hep-statistics); the gate resolves, hashes and strictly validates every ml-artifact
  input (`gate.ml_input_*`); `dependencies.py` propagates unresolved findings (`dependency.source_unresolved`);
  `write_ml_artifact.py` records tool outputs in `extension.source_files`, not `inputs`. `dependencies.py` on J9: exit
  1 -> 0.
- **Writer does not trust self-reports (ML-C06, K11, C07).** The split verdict is recomputed from the report body; the
  test split is the manifest's `roles.test`; a pass without a report is not-run; no status label is exit 2.
- **CLI contract (ML-C17).** Invalid input exit 2 without traceback, missing PyTorch exit 3, `--status` echoed as
  `status_label` on the data-report scripts.
- **Routing, handoffs, size (ML-R19, K15, R20, R35).** 17 routing cases (en and zh-Hant) for task types without one; a
  Task routes index in `ml-analysis.md`; handoff tests for hep-theory, hep-analysis, detector-response, hep-computing
  and research-communication; references 257 KB -> 179 KB (nothing moved to hep-computing: it already had the
  authoring rules). Live routing: pending.

- **Batch commands refused in protected mode (HC-10, HC-16; review of deferred task P6.2).** In a project whose
  config carries `agent_policy`, `core/partition/campaign.py` refuses a real `submit`, `resubmit` or `cancel` and
  `confirm`, `abandon`, `reset` and `clear-orphans` in any form with `protected.batch_needs_trusted_submitter`, before
  any scheduler call. Before, a protected project with valid inputs could submit in-process as in S0 (jobs failed on
  the workers, where the copied runner refuses, but the submission itself ran). `abandon`, `reset`, `cancel` and
  `clear-orphans` also check the protected inputs now. Dry runs, `plan`, `freeze`, `status`, `watch`, `reconcile`,
  `merge` and `report` are unchanged; outside protected mode nothing changes. The switch is protected mode (DP-2), not
  the campaign config; `docs/agentic-architecture.md` §10.2 now says the same for the trusted submitter. Tests:
  `tests/core/test_partition_protected_batch.py`; the bypass suite lists these entry points and declares
  `REFUSED_IN_CONTROL` for consumers such as the deployment's live C07 check.
- **Protected-input source checks: sticky directories documented as refused for the running account.**
  `core/protected/trusted_input.py` refused a protected input below a world-writable sticky directory
  (`/tmp`, the macOS shared folder) for the running account, because its `os.access` check ignores the sticky bit, while
  its docstring promised the sticky exception. The behavior stays (an ACL can grant a deletion the mode bits do
  not show); the docstring now says so. Found by the deployment's live C07 run (release volume under
  the shared folder), which moved its mount point instead. Documentation only.
- **Decision recorded: no capability IDs for permits and analysis-level bundles (task P3.4).** `core:formal-use-permit`
  and `core:analysis-bundle` are not added to `KNOWN_CAPABILITIES`: permits and bundles are sidecars read as protected
  inputs and verified by `contracts/permit.py` and `contracts/analysis_bundle.py`, and no artifact declares a dependency
  on them. Stated in `docs/agentic-architecture.md` §9.3 and at `KNOWN_CAPABILITIES`. Documentation only; contracts
  2.7.0 unchanged.
- **Architecture and deployment documents brought to 0.9.0.** `docs/agentic-architecture.md`: status line names the
  release; §12 labels name the release that introduced each component instead of "Unreleased"; §3 and §9.3 list every
  sidecar (revocation log and head, exposure and decision records, qualification record, analysis-level bundle, permit,
  scan submission and verdict) and the protected-use package; §4 defines protected mode, protected input, revocation log
  and head, qualification record, exposure and decision records, analysis-level bundle and permit; §6.3 adds the
  release-manifest inputs `--revocation-log`/`--revocation-head` and `--exposure-record`, and the project-config example
  is schema 1.2.0 with `nonce_ledger`; §6.5 names the scan-service interface; §8 adds the roles of the transforms,
  release preparation, protected-use guard, lineage and revocation tools, bundles and permits, and the scan interface,
  and the protected-mode refusal of a copied batch runner; §9.1 names analysis-level bundles and the permit's review
  rule. `docs/deployment-model.md`: the release-manifest interface lists `exposure_record` and a verified revocation
  status. Documentation only.

### detector-response (audit DR-WP1 to DR-WP4)

- **Cherenkov photon yield carries z^2 (sci-fix, DR-WP1-01).** `cherenkov_angle.py` and four references: helium at
  40 GeV/c, n = 1.05 gives 68.08 expected photons (was 17.02, 4x low); species take `mass:charge`, `--rigidity` sets
  p = zR.
- **Gaisser-Hillas profile stable at any X_max (sci-fix, DR-WP1-02).** log1p form without cancellation, doubling
  bracket without the fixed 1e6 cap: X_max = 1e20 gives FWHM 1.824036e11 in 0.03 s (hung before).
- **Script physics (sci-fix, DR-WP2-06).** Calorimeter fit weights by a constant relative error without per-point
  errors (constant term unbiased in toys), refuses percentages and reports a negative squared term as a failure; PID
  refuses electrons in the heavy-particle Bethe formula and uses water I = 79.7 eV; multiple scattering derives
  beta(R) from mass and charge and solves crossover and MDR with it; tag-and-probe names its central interval;
  pileup checks bin order and reports input totals; front-end `--channels`/`--cells` integers and a `leakage-scale`
  subcommand.
- **References corrected (sci-fix, DR-WP1-05, DR-WP1-06, DR-WP3).** Pileup reweighting on the Poisson mean mu;
  background-subtracted tag-and-probe yields need a simultaneous pass/fail fit (hep-statistics); calorimetric space
  instruments are not spectrometers; the Störmer cutoff is east-west asymmetric; the appendix edit list applied
  where a source was opened (deferred rows listed in VALIDATION.md); one home each for the equations, the chain and
  the fourteen questions; residual sign convention in the glossary (signed track coordinate).
- **Every script prints a status label and JSON errors (DR-WP2-05).** `--status` (input file's status by default for
  the three file-input scripts), JSON on stdout at exit 2, exit 1 for failed computations.
- **Response hardening, contracts 2.8.0 (DR-WP2-01 to -04).** `validate.py` rules R1-R10 (`_response_hardening`,
  overlay `ext_response_v2_8.json`): declared intended use and flow handling, misspelled keys, placement, exposure
  contains acceptance and live time, flow vectors, correction space, finite-MC statistics for unfolding, variation
  shapes, and the numbers of an inline matrix. Of 30 crafted broken responses `validate.py` now refuses 28 (5 before);
  the two others pass with warnings by design. `response_adapter.py` reads `file.json#key` and flow vectors from the
  ref, refuses refs outside the artifact folder and exits 2 on unreadable refs. SKILL.md step 5 names both checks.
- **Shipped examples carry resolvable responses (DR-WP1-04).** `ams-flux-ratio` writes one response per species and
  period with `matrices/response_<species>_<period>.json` and declares exposure once with its correction space;
  `collider-angular` points at `matrices/response.json`. All five pass `response_adapter.py --validate`.
- **Tool contracts (DR-WP2-07)** for tag-and-probe, PID separation, calorimeter resolution and pileup reweighting;
  `tool_contract.py` reads options of a required mutually exclusive group.
- **Coverage (DR-WP4).** Finite-MC response covariance, fakes, time-dependent responses, a worked 2x2 example and the
  two-tool table; response systematics; resolution models and data-driven resolution; luminosity calibration (vdM);
  calibration pitfalls; ML-reconstruction and fast-simulation validation; JES chain; spectral breaks and the proton
  knee; instrument-response checklists. AMS-02 profile: Layer-0 status by claim ID, solar cycle 25 phase.
- **Hep-analysis docstring (DR-Q1).** `geomagnetic_cutoff.py` states the east-west asymmetry; its dipole default is
  unchanged (follow-up for hep-analysis).

## 0.9.0 (2026-10-14)

Contracts 2.7.0 (unchanged). Release B of the agentic-completion plan (PR #74): formal-use permits and analysis-level
bundles, blinding transforms and release preparation, tool contracts, the scan-service interface, `--strict-versions`.

- **`--strict-versions` (validate.py, dependencies.py).** The stricter version policy alone (a newer minor contract
  version is an error, for the artifact and every source), which `--protected` meant before 0.8.0. It does not switch
  protected mode on, so it needs no protected inputs and is never refused for their absence. `--protected` keeps its
  0.8.0 meaning (protected mode); the library parameter is `strict_versions=`. Tests in
  `tests/contracts/test_strict_versions.py`.
- **Formal-use permits, analysis-level bundles and the recipe-use review (tasks P5.1-P5.3; C15, C08).** New
  `contracts/analysis_bundle.py` (`analysis_bundle.json`): one digest over the measurement spec, recipes, semantics
  tables, calibrations, tool contracts, environment lock, reviews and the plugin release; `verify` reports each change;
  an attestation may take it as its subject. New `contracts/permit.py` (`permit.json`): a custodian-issued permit, read
  only as a protected input, binding the bundle and the digests of the inputs, one purpose, an actor, a nonce counted
  in the custodian's nonce ledger (`agent_policy.protected_inputs.nonce_ledger`), a validity window and the
  attestation whose review must accept the recipe for the required roles and cover the use (`permit.*` codes;
  revocation kind `permit`). Formal use in protected mode now runs with a valid permit (`hepdata_export.py --permit`,
  `build_tables(..., permit=)`) and stays refused without one; the core guard takes the check as `formal_check`.
- **Input-blinding transforms, release preparation and residual checks (task P4; C02).** New
  `core/blinding/transforms.py` for the modes `binned-mask`, `event-removal`, `common-offset` (continuous quantities
  only) and `common-scale` (no per-event weights): released data, sealed values and the `protected`/`retained` lists,
  with keys as inputs only and input uncertainties masked or withheld. New `core/blinding/residual.py`
  (`residual_checks`: codes such as `offset.boundary`, `scale.quantization`, `removal.totals_elsewhere`) and the
  counterexample suite `tests/core/test_blinding_residual.py`; `core/blinding/README.md` states what each mode does not
  protect. New `contracts/release_prepare.py`: the release directory, the sealed file outside it and a draft manifest
  that passes `release_manifest.py` with every custodian option.
- **Tool contracts and scopes (task P5.4).** Contracts for `release_prepare.py`, `mask_blinded_bins.py` and
  `audit_blinded_outputs.py` (per-subcommand operations: `tool_contract.py` now compares each subcommand's own usage
  line); scopes `contracts/tool_scopes/{fixed-execution,validation}.json` checked in CI.
- **Rules settled in the release-B review.** A formal-use permit must cover every input file, directories expanded
  (links refused), and a use with no input file is refused; an S3-execution permit binds the frozen execution bundle
  that runs; every recipe in the analysis bundle must be the attested one; a relative attestation path is read from
  the project. Release preparation builds and checks everything before writing, creates files exclusively (the sealed
  file owner-only, 0600), compares resolved paths, and refuses an existing sealed file, a `release_id` with path
  characters and a manifest over the sealed file. The scan budget is charged by the service's recount of the received
  bytes (never less than the submission states) and stays exhausted once refused. Residual checks recognize identifier
  fields by name tokens (camelCase included), scaled counts up to 10^5 at float precision, and integer residues at
  large values. Bad bundle refs and duplicate JSON keys are refusals.
- **Scan-service interface (task P6.1).** New `contracts/scan_verdict.py` (`scan_submission.json`,
  `scan_verdict.json`): a closed agent-visible verdict (status and budget state only) and a per-analysis budget
  counted in candidate values tested, charged for every submission.

## 0.8.0 (2026-10-14)

Contracts 2.7.0 (minor: the capability IDs `core:revocation-log`, `core:exposure-record`, `core:decision-lineage` and
the warning `exposure.capability_not_declared`; a 2.6 artifact keeps its outcome; the data release manifest sidecar
keeps `manifest_version` 1.0.0;
new sidecars: revocation log and head, exposure and decision records, qualification record). Project config schema
1.2.0 (`agent_policy.protected_inputs`). A project with `agent_policy` now runs in protected mode (see below).

- **Custodian checks in the release-manifest checker (AGENTIC-R5 T1.2, deployment work package B).** The checks a
  custodian deployment ran on its own side move into `contracts/release_manifest.py`, so every custodian uses one
  tested implementation. Always on, from the manifest alone: a transform parameter name that looks like key material
  (`KEY_LIKE`: key, secret, offset, scale, seed, password, token) is `release.keys_present`, a wildcard in a destination
  is `release.destination_wildcard`. New options (keyword-only in `check()`, flags on the command line; each adds
  checks and none is needed for a pass): `--code-digest` (`release.transform_code_mismatch`), `--destination-sets`
  (`release.destination_set_unknown`: the destinations must equal one held set exactly), `--analysis` (release history:
  `release.related_incomplete`, `release.related_unknown`, warning `release.related_revoked`; ledger entries may carry
  `analysis` and `source_sha256`), `--sealed` (every artifact scanned for a sealed value with `core.blinding`, JSON
  objects without their structure keys: `release.sealed_value_present`; an artifact that cannot be scanned is
  `release.scan_incomplete`, fail closed). Findings name the artifact only, never a sealed value or a count. Passing
  still releases nothing. Tests in `tests/contracts/test_release_manifest.py` (`CustodianOptionTests`).
- **Protected-use mode at the formal-use entry points (task P1; C07 plugin part, HC-09, K08, DP-2, DP-4).** A project
  whose config declares `agent_policy`, or an entry point given `--protected`, now runs in protected mode; omitting a
  flag cannot switch it off, and outside protected mode nothing changes. In protected mode every formal-use entry
  point of the R5.4 code change map (validate, dependencies, comparison gate and check, combination plan, model set,
  `combine_measurements.py`, HEPData export and record, `batch_campaign.py` and campaign submit/resubmit/confirm/merge,
  the runner, `engine.run`/`merge`, `local_partition.py`, `bayes_diagnostics.py`, template fits, change review,
  `mask_blinded_bins.py` and the `core.blinding` entry points, `project.load_project`, `environment_manifest.py`, the
  evidence ledger, `check_manuscript.py`) first reads the authoritative copy of the policy named by
  `agent_policy.authoritative_copy` and, from it, `protected_inputs` (project schema 1.2.0): the revocation log and
  head (verified as in P2) and the new qualification record (`qualification_record.json`: valid now, bound to the
  authoritative policy's digest and to the running plugin's code identity, not revoked). Each must be a protected input
  the session's account neither owns, nor can write, nor can replace. A failure, a revoked input file or an input that
  needs an unknown capability is a refusal: command lines exit 3 with `{"status": "refused", "refusals": [{code, path,
  message}]}`, report-returning functions add `protected.*` error findings, other functions raise
  `ProtectedUseRefused`. Formal use (HEPData export for publication) is refused in protected mode until formal-use
  permits exist (release B). The guard is the new standard-library package `core/protected/` (`guard`,
  `trusted_input`, `revocation_log`, `identity`, moved from `contracts/` so that `core/` functions call it; the
  `contracts.identity` and `contracts.revocation` import paths are unchanged), with `contracts/protected_use.py` as the
  public interface (`status` command). `comparison/gate.py`: the comparison logic is `_gate`; the public `gate` and
  `check` check protected use first (refusal `protected-use`). The copied batch runner cannot check the inputs and
  refuses in protected mode (exit 3; protected batch execution runs through the trusted submitter). Instruction-text
  rules P01-P03 report wording that calls these checks an authorization or a bypass; skill references (hep-computing
  engineering playbook, hep-analysis analysis design, hep-statistics combinations) describe protected mode and exposure
  records. Bypass suite `tests/contracts/test_protected_entry_points.py`; fixture `tests/protected_fixture.py`.
  Rules settled in review: a directory the session's account owns is replaceable even when read-only; an input is
  revoked by its byte digest, its canonical JSON digest or its project-relative path, and an input that cannot be read
  is refused (`protected.input_unreadable`); a qualification is revoked by id or digest; a link into a protected
  project is followed when the mode is decided; a project config that cannot be read, or a malformed one that names
  `agent_policy`, switches protected mode on (`protected.config_unreadable`); `authoritative_copy.sha256` is the canonical
  JSON SHA-256 of the policy without `authoritative_copy`, as the deployment's launcher computes it; malformed protected inputs are refusals,
  never crashes (`protected.input_malformed`); in protected mode an exposure record is read only as a protected input.
- **Exposure and decision lineage (task P3; C12, T1.9, T4.3).** New sidecars `exposure_record.json` (per analysis and
  source snapshot: entries `{seq, release_id, via: session|relay, seen: [closed kinds], time, actor}`, each version
  naming the canonical SHA-256 of the previous one) and `decision_record.json` (decision, category, actor human or
  agent, `seen: {through_seq, entries_sha256}`, artifacts, `recipe_sha256`), checked by the new `contracts/lineage.py`
  (`lineage.*` codes; command line `lineage.py exposure|decision`). `derive_exposure()` is the one mapping to the
  envelope `data_exposure`: `exposed` once an entry names `signal-region`, `unblinded-result` or `sealed-value`,
  `unknown` (never `unexposed`) for a missing or invalid record; appends cannot clear exposure. Producers use it:
  `review_analysis_change.py --exposure-record FILE` and `batch_campaign.py freeze --exposure-record FILE`.
  `release_manifest.py --analysis ... --exposure-record FILE` (`check(..., exposure_record=...)`) refuses a release the
  record knows but `related_releases` omits (`release.related_incomplete`) or the ledger does not know
  (`release.exposure_release_unknown`). The reverse index follows exposure records (release -> record) and decision
  records (recipe -> decision -> artifacts). Capability IDs `core:revocation-log`, `core:exposure-record` and
  `core:decision-lineage` join `KNOWN_CAPABILITIES` (contracts 2.7.0; a 2.6 reader refuses an artifact that requires
  one); the validator warns `exposure.capability_not_declared` when a structured `data_exposure` names
  a record without `core:exposure-record`. Tests in `tests/contracts/test_lineage.py`.
- **Hash-chained revocation log and reverse index (task P2; C07, F07).** New `contracts/revocation.py` with the sidecar
  schemas `revocation_event.json` and `revocation_head.json`: a genesis record and events `{seq, prev_sha256, subject:
  {kind: artifact|release|recipe|source|attestation, ref and/or sha256}, reason, time, actor}`, each binding the
  canonical SHA-256 of the record before it, and a head `{count, last_sha256, as_of, source}` written by the custodian.
  `verify()`/`load()` refuse an empty or unterminated file, a gap, an edited or reordered record, a truncated log, a head
  for another log, from another source, stale or dated in the future (`revocation.*` codes); a refused log answers no
  lookup instead of "nothing revoked". `build_index()`/`affected()` follow envelope inputs, `data_exposure.record_ref`,
  release manifests, attestations, bundles and recipes to every dependent, transitively, without writing anything.
  New `core/protected/trusted_input.py`: in protected mode a protected input must be a regular file with one link that the
  running account neither owns, nor can write, nor can replace along its path (`source.*` codes).
  `dependencies.py --revocations` now reads the chained log (`--revocation-head`, `--revocation-source`,
  `--max-status-age`, `--now`); the legacy JSON Lines format is a warning (`dependency.revocations_legacy`) and is
  refused with `--protected`; an empty legacy file is an error. `release_manifest.py` and `attestation.py` take a
  verified log (`--revocation-log`, `--revocation-head`, or a `RevocationStatus` in `check()`/`evaluate()`) as their
  status source, filtered by subject kind (`release.status_unverified`, `attestation.status_unverified`). Tests in
  `tests/contracts/test_revocation.py`.
- **Architecture and deployment documents.** New `docs/agentic-architecture.md` (objectives, constraints HC-01 to
  HC-18, planes, blinding modes, release manifest, host enforcement points, guard, stages, component roles, the
  scientific-integrity layer, batch architecture, and where each component lives) and `docs/deployment-model.md` (the
  plugin in this repository; the host adapter and custodian in a separate deployment repository; the interfaces a
  deployment relies on; the release-to-deployment procedure; a host-neutral qualification catalog). Documentation
  only; nothing is qualified by them.

## 0.7.1 (2026-10-13)

Contracts 2.6.0 (unchanged). The recipe sidecar gains `recipe_version` 1.1.0 (optional correction keys); 1.0.0 recipes
keep their outcome. Release notes in brief: the R4 correction key for bounded recipes (PR #67) and the skill texts
aligned with R4 §9 scientific-validation guidance (PR #68).

- **R4 correction key for bounded recipes (AGENTIC-R5 backlog, R4 F04/T04).** `recipe.json` accepts
  `recipe_version` 1.1.0 with optional `effect_keys` on the input and on steps: per effect, the key
  `(target_scope, calibration_digest, variation_id, stage)`. `recipe_semantics.py` also reads these fields from upstream
  `extension.corrections[]` entries. A second application of an effect on the same target scope and variation is
  `semantics.repeated_correction` whatever its calibration or stage; on another scope or variation it is not blocked
  (warning `semantics.repeat_distinct_instance`, for review); a repeat where either side lacks a complete key is
  `semantics.repeat_undetermined` (supply the keys). Unkeyed recipes keep the effect-name rule; keys on a 1.0.0
  recipe, a key for an effect the step or input does not apply, and an input key that differs from the upstream record
  are errors. The operator-semantics table (`differential_flux.json`, approved 1.0.0) is unchanged. Tests in
  `tests/contracts/test_recipe_semantics.py`.
- **Scientific-validation wording aligned with R4 §9 (AGENTIC-R5 backlog).** Statements that were stronger than the
  method allows are qualified: optimizing on the measured events is biased unless a validated pre-designed procedure
  (cross-fitting, k-fold) removes the bias, keeping performance evaluation, method selection and formal inference
  apart (hep-analysis `analysis-design.md`); a core tool's own tests count as closure only for the model they test
  (hep-statistics `SKILL.md`); detector closure is labelled same-model and needs a model-mismatch test or a control
  sample beside it; "independent implementation" states what is shared, and agreement is evidence, not proof. Added:
  injection tests and pulls judged on toy ensembles, with a toy oracle for low counts and boundaries
  (`likelihood-fitting.md`); a closure taxonomy and N-version caveat (`numerical-and-computational-methods.md`);
  chunk-merge preconditions and the event-order caveat (hep-computing `SKILL.md`, `analysis-data-pipelines.md`); the
  guarded period-agreement null test (`correction-chain.md`); holdout tiers and generator-family variation
  (physics-ml `evaluation-strategy.md`); quarantine for what a loop learns and variant sets with registered blind
  spots in bug fixes (`loop-engineering.md`, `engineering-playbook.md`).

## 0.7.0 (2026-10-13)

Contracts 2.6.0 (minor: theory-spec, prediction, measurement-spec and statistical-result hardening rules; optional
fields only; every 2.5.0 artifact keeps its default outcome and gets the new rules with `validate.py --strict`, at the
same level, and at the publication gate; no new capability).

Release notes in brief: four skill audits (hep-analysis, hep-computing, hep-statistics, hep-theory; PR #64) and their
follow-ups (PR #65). Test-only release fix: the gate test that inlines the sbottom benchmark artifact ignores its plugin
version string, which every release rewrites.

### hep-theory

- **theory-spec and prediction semantics (contracts 2.6.0).** `ext_theory_spec.json` gains optional `limit`,
  `neglected`, `computational_run_ref`, `degenerate_directions`, `model.family`, `checks_run[].tolerance` and
  `references_read[].date_read`; `ext_prediction.json` gains `derivation_status`; `uncertainty_component` gains
  `prescription`, `method` and per-bin `bounds`. New core vocabularies `envelope_prescriptions`, `truncation_methods`
  (including `not-estimated`) and `check_results`. New checks (native from 2.6.0): an `observed` prediction, or a
  `validated-in-scope` one without a linked theory-spec input carrying that status, a perturbative argument without
  an order, an asymptotic argument without a limit, a formal proof or analytic derivation with no check run, a check
  result outside the vocabulary, an empty validity domain, a scale envelope without a prescription or with values
  that are not one [min, max] pair (or bounds that do not match the bins), and a `cosmic-ray-propagation` model
  without degenerate directions are errors; a prediction with neither `theory_spec_ref` nor `derivation_status` is
  unresolved; a missing core convention key and a truncation without a method are warnings.
- **Scripts refuse what used to give a wrong number.** `pdf_uncertainty.py` accepts `symmhessian+as`, `hessian+as`
  and `replicas+as` (the last two members are alpha_s down and up, reported as a separate `alphas` object; PDF4LHC21
  Eqs. 6.7-6.8), checks `num_members`, offers `--combine-alphas quadrature` (labelled a prescription) and
  `--symmetrize`, and refuses non-finite members. `eft_truncation.py` refuses `a*b` given with `b*a`, keys that are
  not one pair, blank conventions, an empty operator list, `lambda_tev` <= 0 (was a `ZeroDivisionError`) and
  non-finite numbers, requires `cross_term_convention` for off-diagonal terms, runs the promised rescaling check and
  reports the flag fraction's source. `event_weights.py` refuses negative, out-of-range, repeated and non-integer
  selected indices (an `IndexError` and Python wrap-around before), non-positive cross sections, negative luminosity
  and non-finite weights, and reports the selected sum of weights, sum of squares, effective sample size and relative
  statistical uncertainty. `dis_kinematics.py` refuses points outside the exact lepton-mass bounds y_max and
  Q^2_min(y), reports them, and accepts a target at rest.
- **References.** New `amplitudes-and-widths.md` (phase space and widths from the PDG Kinematics review, narrow-width
  conditions, Breit-Wigner and complex-mass scheme), `selection-rules.md` (procedure, conserved quantities,
  Landau-Yang, Furry, helicity suppression, G-parity) and `regularization-and-schemes.md` (CDR/HV/FDH/DRED, gamma_5,
  beta and gamma_m normalizations, pole vs MS-bar, IRC safety). `cosmic-ray-propagation.md` gains kinematics (pointing
  to `core/kinematics/relativistic.py`), the force-field formula with its source and limits (code stays in
  hep-analysis), and antiproton source-term conventions. Each statement cites an opened source with its location and
  read date, or says `unverified`.
- **New theory profile `theory:higgs-bb-width`.** Gamma(H -> b bbar) with the MS-bar running b mass through
  alpha_s^4, the running of mass and coupling derived and checked mu-independent order by order in exact arithmetic,
  and the scale envelope, truncation estimate and parametric alpha_s and m_b variations kept apart.
- Routing cases for selection rules and a scheme conversion (en, zh-Hant). The committed theory examples
  (`qed-prediction`, `theory-comparison`, `recasting`) are written at contracts 2.6.0 with the added fields; their
  numbers are unchanged.

### hep-computing (remediation CMP-01…CMP-28)

- **CMP-01 partition state lock.** `core/partition/engine.py` `run()`, `reset()` and `merge()` hold an exclusive,
  non-blocking lock on `<state>/.lock` (`dir_lock`, shared with `campaign_lock`, so campaign calls still nest); a second
  process gets `PartitionError("partition.locked")`, and `local_partition.py` prints it as a JSON `error` with
  `code`, exit 2. `status` stays lock-free. Tests: `tests/core/test_partition_robustness.py`.
- **CMP-02 atomic chunk writes.** `_write_atomic` serializes first, flushes and fsyncs, and removes its `.tmp-*` file on
  any failure. A worker result that is not JSON-serializable is a failed attempt with signature
  `unserializable-result` (counted; the run continues) instead of a `TypeError` out of `run()`; `merge` ignores dotfiles
  in `chunks/`. A chunk that uses its last attempt is marked `attempts-exhausted` by that same call, not `failed` (Q5).
- **CMP-03 manifest checked by every subcommand.** `local_partition.py status`, `merge` and `reset` validate the
  manifest first (a list or a dict without `chunks` exits 2 with a JSON `error`, no traceback); `reset` writes nothing
  before validation and refuses a state folder of another manifest (`engine.reset(..., manifest=)`) or an unknown chunk.
- **CMP-04 seal only what public data do not reveal (Q3 option a).** `core/blinding` `seal()` drops exact zero and every
  number equal (relative 1e-9, sign ignored) to one the unblinded bins give alone: a sum over any run of unblinded
  bins, the sideband total, or their square roots. A blinded empty bin no longer makes `job finished: 0 errors` or a
  public sideband CSV a leak; a nonzero blinded value is still found. When nothing is left, `audit_blinded_outputs.py
  seal` writes `nothing_sealable: true` and `scan` accepts the empty list. `NOT_SEALED` names both exclusions.
  `tests/core/test_stats_edge_cases.py` updated: 0 is no longer sealed. Tests: `tests/core/test_blinding_regressions.py`.
- **CMP-05 unreadable numpy caches are unscanned.** An object `.npy`, a pickled or non-zip `.npz` and a corrupt zip
  `.npz` (`BadZipFile`) are listed as unscanned: the scan ends `incomplete`, exit 3, instead of exit 2 or a traceback
  with exit 1 (reserved for a found leak).
- **CMP-ANA-P2-7 (core part of hep-analysis audit P2-7) masking fails closed.** `mask_ratio` refuses numerator,
  denominator and mask of different lengths (`zip` truncated them: a 2-entry reference against 4 bins gave a 2-entry
  ratio); `mask_binned`, `mask_ratio` and `seal` refuse strings, booleans and non-finite numbers; `mask_binned(...,
  errors=)` masks an error array with the values' mask; `flow=True` (in `blinded_mask`, `mask_binned`, `seal`) adds
  underflow and overflow bins, blinded when the region reaches past the first or last edge. The script
  `mask_blinded_bins.py` is unchanged here (hep-analysis branch).
- **CMP-06 `compare_root_histograms.py` is a comparison.** Tolerances `--abs-tol`, `--rel-tol` (default 1e-9) and
  optional `--sigma-tol` (difference over combined bin errors); edges checked on every axis; TH2/TH3 compared per
  (x, y, z) bin in ROOT numbering; worst bin by absolute difference, relative difference and pull reported separately;
  one JSON object with `status`; uproot backend when PyROOT is absent (`--backend`). Exit 0 within tolerance, 1 outside
  or shape/edge mismatch (no traceback), 2 bad input, 3 no backend. Tests: `tests/skills/hep_computing/test_compare_histograms.py`
  (uproot, E2); `test_root_integration.py` now parses the JSON (PyROOT).
- **CMP-07 `environment_manifest.py` drift, inputs, project, output.** Records `system` (OS family, architecture,
  libc: compared; kernel release: a note only) instead of comparing `platform.platform()`; also compares `executable`
  and `machine`. `record --inputs FILE...` writes `input_manifest` (`path`, `sha256`, `size`; validates as a
  `computational-run`), `check` reports changed or missing inputs and, with `--project`, a changed commit or a dirty
  checkout. `--out` creates parent folders; an unwritable output is a JSON error, exit 2; `record` prints a JSON
  `status` (`recorded`). `references/environments-and-containers.md` updated.
- **CMP-08 script contract (Q4).** Every Python and shell script of the skill prints JSON with a `status` key (the
  ROOT viewers `inspect_root_file.py`, `summarize_histogram_statistics.py`, `roofit_workspace_summary.py`, plus
  `lint_task.py`, `check_root_cpp_env.sh` and the maintenance validators on `--json`; human text stays the default),
  exits 0/1/2/3 (3: missing optional dependency or incomplete; PyROOT missing was exit 1), and refuses an unwritable
  output without a traceback (`create_story_card.py`, `generate_skill_example.py`, `make_synthetic_nanoaod.py`
  now create folders). `local_partition.py` adds a uniform `status` (planned, complete, incomplete, error);
  `audit_histograms.py` adds `status` and exits 2 on an unreadable file. `inspect_root_file.C` is exempt by name.
  `SKILL.md` invariant 5 and the playbook state the contract; the per-script table is in the skill `README.md`.
- **CMP-09 `new_root_cpp_project.sh` target, overwrite, name.** `--dir DIR` (default `./NAME`); NAME must match
  `^[A-Za-z_][A-Za-z0-9_]*$` before it enters `project(...)` (`bad name`, `../x`, an absolute path exit 2); an
  existing non-empty target is refused (exit 2) unless `--force`; the generated program writes `output.root` and
  `pt.pdf` into an output folder argument (default `output/`); the CMake file links imported `ROOT::` targets and
  takes the standard from `ROOT_CXX_STANDARD`; the build hint is quoted; `--json`. The generated project configures
  and builds against Homebrew ROOT 6.38.04 (test skipped without cmake and ROOT).
- **CMP-10 `check_root_cpp_env.sh` private temporary folder.** `mktemp -d "${TMPDIR:-/tmp}/root_cpp_check.XXXXXX"`
  replaces `$TMPDIR/root_cpp_check.$$` (and no longer reassigns `TMPDIR`); the trap removes it; the test program takes
  `-std` from `root-config --cflags` only. Two parallel runs do not collide and leave nothing behind.
- **CMP-11 `lint_task.py` cited paths stay inside the repository.** Each cited path is resolved (`..` and symbolic
  links followed) and must stay under `--repo` (or the skill root for the fallback); one that escapes is an error
  "path leaves the repository" (an `src/` + 14×`../` + `etc/asl.conf` path was accepted as existing). A path starting
  with `../` is a warning instead of a silent skip; in-repo paths with `..` still pass.
- **CMP-12 robustness test asserts the contract.** `tests/skills/test_cli_robustness.py` gains
  `HepComputingScriptContractTests`: every hep-computing script (both `.sh` included; `inspect_root_file.C` exempt by
  name) must print one JSON object with `status` and the documented exit code for a missing input, a refused target
  and an output path that cannot be created (22 cases fail on c1d375c, including the four output-path tracebacks).
- **CMP-13 `root-balanced-design-guidelines.md` corrections.** R1: writing to a `TFile` does not need `TObject`
  (`WriteObject`/`Get<T>` for any class with a dictionary; non-`TObject` branches); `TObject` is for `TList`/`TObjArray`
  containers, `TObject*` APIs and directory registration. R2: `ClassImp` is not needed in ROOT 6; `ClassDefOverride`
  only adds `override`; `#pragma read` rules instead of a hand-written `Streamer()`. R3: one baseline, C++17, `-std`
  from `root-config --cflags`. R4: the double delete is order-dependent (`~TH1` deregisters); the hazard is a smart
  pointer outliving its file; callers own non-registering `Get` results (`TGraph`, `TF1`, `TCanvas`, `TVectorD`);
  `TH1::AddDirectory(kFALSE)`; `RResultPtr` ownership; the demo now compiles (checked against ROOT 6.38.04). R5:
  `gRandom` in `Define` under IMT, `DefineSlot`, eager `Snapshot` unless `fLazy`, `Range` unsupported with IMT,
  non-deterministic order and sums. R6: "CINT" dropped. R7: one rule each for naming, non-owning members (pointer),
  `std::filesystem` and exceptions, stated once at the top.
- **CMP-14 `cmake-and-build.md` imported targets, one C++ baseline (Q2).** The minimal project links
  `ROOT::RIO ROOT::Tree ROOT::Hist ROOT::Gpad ROOT::ROOTDataFrame` and sets the standard from `ROOT_CXX_STANDARD`
  (no `ROOT_INCLUDE_DIRS`/`ROOT_LIBRARIES`, no second `-std`); configures, builds and runs against Homebrew ROOT
  6.38.04 with CMake 4.3.2. `cpp-balanced-design-guidelines.md` now states the same C++17 baseline and marks its
  C++20 examples "C++20 only".
- **CMP-15 `bash-balanced-design-guidelines.md`.** B1: sourcing `thisroot.sh`, an LCG `setup.sh` or `module load`
  under `set -u` fails; wrap in `set +u` … `set -u`. B2: `"${arr[@]}"` on an empty array fails under `set -u`
  before Bash 4.4 (macOS `/bin/bash` 3.2; checked on 3.2.57), with the `${arr[@]+"${arr[@]}"}` guard. B3: no
  `/var/lock` (root-owned, node-local) and no `flock` on NFS/EOS/AFS/Lustre; lock in local scratch. B4: the EXIT
  trap does not stop children; forward SIGTERM to the child and `wait` (preemption), exit 143; checked on Bash 3.2.
  B5: the bad-comment example no longer uses `((i++))`.
- **CMP-16 `python-hep-coding-patterns.md`.** P1: `with ROOT.TFile.Open(...) as f:` / `with uproot.recreate(...)`
  instead of "close output files explicitly", consistent with the Python guidelines. P2: `ROOT.SetOwnership` and the
  pitfall of a histogram drawn in a helper vanishing from the canvas. Checked with PyROOT 6.38.04.
- **CMP-17 new reference `crash-and-memory-debugging.md`.** Decision rules (reproduce, shrink to one thread and few
  events, first frame in own code, symbols, stop rule), ROOT's stack trace and `gDebug`, gdb/lldb on `root.exe`,
  valgrind with `$(root-config --etcdir)/valgrind-root.supp`, ASan/UBSan through CMake and their limits with ROOT,
  ACLiC `+g` and the stale-library pitfall, a crash-cause table, and leak triage (RSS against events with
  `gSystem->GetProcInfo`, `gObjectTable`, the directory that holds histograms, jitted RDataFrame strings). Linked
  from `root-debugging.md` and a new "References of the hep-computing skill" section in the playbook.
- **CMP-18 new reference `performance-profiling.md`.** Target in the acceptance criteria and a stop rule; wall time
  and peak RSS first; `perf record -g`, `cProfile`, `py-spy`; RDataFrame one loop (`GetNRuns`, checked 1 then 2),
  `RunGraphs`, IMT and jitting caveats, lazy `Snapshot`; `TTreePerfStats`, cluster and basket sizes (default
  auto-flush 30 MB), branch selection, compression; uproot `expressions`/`filter_name` and `step_size`; batch sizing.
- **CMP-19 new reference `symbolic-and-numerical-computation.md`.** SymPy assumptions, the limits of `simplify`, a
  numeric identity check at random points, `lambdify`, exact rationals; `quad` error estimates, endpoint
  singularities, `points`, a narrow peak missed silently (and still with `points`) until the range is split,
  infinite and oscillatory ranges; `solve_ivp` method choice (RK45 729,668 against Radau 726 evaluations on a stiff
  system), `rtol`/`atol`, the rtol/10 check, events, status; `brentq`, `minimize` status. Every number from a run
  with SymPy 1.14.0 and SciPy 1.18.1; points to `find_python.py` and the validation ladder.
- **CMP-20 current stack.** `root-balanced-design-guidelines.md` gains "RNTuple and current RDataFrame features":
  RNTuple versus TTree (format 1.0 final since 6.34, types in `ROOT::` since 6.36; read by RDataFrame and by uproot
  5.7.6), `Vary`/`VariationsFor`, `DefinePerSample`, `FromSpec`, `DefineSlot`/`rdfslot_`, distributed RDataFrame with
  `executor=` (6.36; the `Experimental` path removed in 6.38), `AsNumpy`/`FromNumpy`; all run with ROOT 6.38.04 and
  cited to the 6.34/6.36 release notes. `python-hep-coding-patterns.md` gains link-level guidance for hist and
  boost-histogram, vector, correctionlib, coffea, dask-awkward and numba. `performance-profiling.md` notes the 6.38
  `Snapshot` compression default (505).
- **CMP-22 Slurm `MaxArraySize` preflight.** `slurm_backend.py` reads `MaxArraySize` from `scontrol show config`
  before `sbatch` and refuses (`slurm.array.too_large`, attempts not-submitted, no `sbatch` call) an array whose
  largest index is not below it; an unreadable value leaves the decision to `sbatch`. New fake `scontrol` in
  `tests/adapters/batch_shims/`; tool facts table row added. Tests: `tests/adapters/test_batch_cmp_regressions.py`.
  (Also: the CMP-07 git test no longer uses an e-mail-shaped placeholder, which the packaging check flags.)
- **CMP-23 Slurm `DerivedExitCode`.** `SACCT_FIELDS` gains `DerivedExitCode`; a job row `COMPLETED 0:0` with a
  nonzero derived code (a failed `srun` step) is `failed` with the derived exit code and `failure_reason`
  `derived-exit`. `core/partition/states.signature` appends `reason=<failure_reason>` when a backend sets one (older
  records keep their signature), and `campaign._apply` carries the field. 8-field sacct recordings still parse. The
  fake `sacct` emits the field; `examples/batch-partition/output/results.json` regenerated (the new `scontrol` call
  count from CMP-22, nothing else changed).
- **CMP-24 HTCondor event 002.** `parse_event_log` maps event 002 (error in executable) to `failed` with
  `failure_reason` `executable-error` (signature `...|reason=executable-error`) instead of leaving the job queued and
  asking `condor_q`; a later hold event still wins. The fake `condor_submit` gains an `executable-error` fault.
- **CMP-21 bookkeeping.** `SKILL.md` Owns names `core/blinding` and `core/partition`; skill README counts (thirty-two
  references, twelve test modules) and links to the new references; three static routing cases (`co-cmp-crash-1`,
  `co-cmp-perf-1`, `co-cmp-ode-1`, all hep-computing, triggers from the existing description) in
  `tests/routing/make_cases.py`, `cases.json` regenerated; capability-matrix rows for blinding, local partition,
  ROOT tools, task authoring and the environment manifest updated; VALIDATION section CMP-REMEDIATION.
- **CMP-25 design guidelines consolidated (Q1).** `root-balanced-design-guidelines.md` keeps the ROOT-specific rules
  (TObject or plain C++, dictionaries and I/O, directory ownership, ROOT globals, errors at the ROOT boundary,
  dictionary limits of templates, naming/comments/file headers for every language, build layout, RDataFrame and
  RNTuple patterns, checklist) and the shared conventions; the generic class/struct/inheritance/state/testing
  sections and the toy examples are gone. `cpp-`, `python-` and `bash-balanced-design-guidelines.md` are checklists
  around HEP failure modes with grep-able anti-pattern tables; the CMP-13..15 rules are kept. Four files: 4,573 →
  1,028 lines; file names and linked anchors unchanged. `docs/reference-consolidation.md` records P1 as executed.
- **CMP-26 off-domain material moved (Q1, Q6).** `product-framing.md` moved to `docs/dev/engineering/` (`git mv`);
  the playbook's New Endpoint, UI Feature, Database Migration and Incident Response sections, the Sprint planning
  and Feature flags sections of `design-and-estimation.md` and the Accessibility section of `risk-and-quality.md`
  moved to `docs/dev/engineering/web-and-delivery-practices.md`, with a one-line pointer at each old place and the
  skill's links re-pointed. `prompt-engineering-and-token-optimization.md` stays (the bundle validator and the task
  guide require it). The skill now has thirty-one references.
- **CMP-27 deferred (Q1).** The six task- and example-authoring scripts stay in `skills/hep-computing/scripts/`:
  task and example authoring remain in the skill's scope.
- **CMP-28 physics-code worked example.** `examples/physics-code-task.md`: prove that the RDataFrame cutflow asset
  reproduces a `TTreeReader` event loop bin for bin (zero-tolerance `compare_root_histograms.py`, bin errors
  compared separately, single- and multithreaded, deliberate mutations must fail); passes `lint_task.py --repo` and
  the example tests; listed in `examples/README.md`.

### hep-analysis

- **Flux bin-width unit.** `cosmic_ray_flux.py` requires `--bin-width-unit {GV,GeV,GeV/n,TeV,TV}` and echoes
  `bin_width_unit`; the guide's check-first row passed a 1.2-1.8 TV bin as 0.6, which makes a flux per GV 1000x too
  large (now: 600 GV). Detector-response commands and the tool contract follow.
- **Bounded flux intervals.** `cosmic_ray_flux.py` now reports an interval on the signal mean s >= 0 from core/stats:
  Garwood for any count (the 500 ceiling is gone), Feldman-Cousins for a known background, Cousins-Highland by
  default for an uncertain one (labelled approximate), `--method profile-fc --toys --seed` for publication use. No
  bound is negative; `flux_upper_limit` when the lower end is 0. The old subtraction is `--method naive`
  (approximate, clipped at 0). Above the FC grid limit it exits 3 and names the alternative. New
  `--exposure-rel-uncertainty` gives `flux_syst_exposure`.
- **One CLI contract.** All twelve scripts take `--status` (core statuses; tables also `published`) and report it;
  exit codes 0 ok, 1 finding or failed computation, 2 invalid input or usage (NaN, inf, malformed files), 3
  incomplete; one-line errors, no tracebacks. `make_yield_table.py` requires `--status`;
  `check_systematic_variations.py` defaults to JSON.
- **One spec format.** `assets/analysis-contract.yaml` and `systematics-config.example.yaml` are removed; new
  `assets/measurement_spec.template.json` (validates with `--strict`) and its field guide. `systematics.csv` uses the
  spec's systematics ledger columns; `systematics_table_tex.py` renders them.
- **measurement-spec semantics (contracts 2.6.0).** `MEASUREMENT_SEMANTICS_FROM = "2.6.0"`: estimand sentence,
  complete observable (phase space, frame, unit and binning), conditional denominators, backgrounds with estimator,
  control region or constraint and closure, each correction once from the controlled categories (factorized
  efficiencies allowed), no zero for unknown, systematics with `applied_via` and unique names, missing markers listed
  in `unresolved_inputs`, blinded specs with a mask and without `observed` status, ratio blocks, ordered periods,
  misspelled keys. New optional schema fields: `estimand`, `no_backgrounds_reason`, background `control_region`,
  `constraint`, `closure`, correction `exact_zero`, blinding `mask` and `unblinding_record_ref`. The 30-mutation probe
  went from 30 silent passes to 2 (both by design). `validate.py` accepts flags before the artifact path. Example
  specs gain an estimand and drop the double-listed luminosity and exposure corrections.
- **Review procedure.** New `references/review-and-artifacts.md` (verdict scale `blocked` / `needs-work` /
  `acceptable-with-open-inputs`, output order, checklist, measurement brief, worked review of a synthetic defective
  spec) and `assets/measurement-review-template.md`; the AMS module links it.
- **Correlations.** One rule in SKILL.md, README, references, routing contract (new ownership row `correlation
  evidence`) and the hep-statistics handoff line: hep-analysis supplies the evidence and a proposed scheme,
  hep-statistics encodes it and checks positive semidefiniteness.
- **Guide re-scoped** (219 to 106 lines): code-level material (API selection, pipelines, code-file requirement, the
  RDataFrame normalization code) moved to `skills/hep-computing/references/analysis-data-pipelines.md`;
  `data-pipelines.md` is a pointer; link checker test for `skills/hep-analysis/**/*.md`.
- **Physics corrections** with primary sources: solar cycle 24 phases (SILSO), cutoff selection rule and exposure
  formula, sigma(Xmax) for p and Fe (Kampert & Unger 2012), ratio cancellation, trials (Gross & Vitells 2010), Garwood
  N = 0 footnote, Barlow's rule, Peelle's Pertinent Puzzle.
- **SKILL.md** 8157 to 7771 B; one home per invariant (blinding rules only in `analysis-design.md`); workflow step 5
  names the `validate.py` command.
- **Scripts.** Orbit cutoff: tilted-dipole ground-track mode with time fractions and an exposure-versus-cutoff table.
  Geomagnetic cutoff: AME2020 nuclear masses, `--radius-re` (old `--altitude-re` deprecated). Force field:
  `--energy-kind`, `--phi-unit`, `--phi-uncertainty`, `--lis-table`, conversions via core/kinematics, NaN exit 2.
  Power-law fit: continuous sharp or smooth broken power law with a free break, chi2/ndf, p-value, covariance,
  asymmetric errors, Lafferty-Wyatt centres, pivot normalization; `--break-energy` now fixes the break of the
  continuous model. Systematic variations: statistical normalization and shape tests with bin uncertainties, flow
  bins for JSON. Blinded-bin masking fails closed on length or type mismatches and masks errors and flow bins.
  Change review: outcome and signal-region wording, strict booleans, new `needs-human-review` decision. Ratio:
  exact `poisson-ratio` and `binomial-fraction` methods. Tables: escaping, `--totals`, safe LaTeX labels.
- **Method content.** New `references/correction-chain.md` (factorized efficiencies with denominators, data/MC
  ratios, time-dependent measurements, nuclei and isotopes, neutrino and fixed-target specifics); estimand and fiducial
  definitions and steeply falling spectra in `measurements-and-unfolding.md`; systematics budget; antiparticle
  backgrounds; trigger efficiency from data, unbiased optimization and look-elsewhere at the design stage in
  `analysis-design.md`. Each has a synthetic worked example checked by `tests/skills/hep_analysis/test_method_references.py`.
- **Spec review script.** New `scripts/review_measurement_spec.py` drafts a verdict-first review from the validator
  findings; the collider and cosmic-ray examples run it and write `review.md`.
- **Tests and records.** Behavioural invariant tests replace the guide-wording test; 14 new routing cases (en and
  zh-Hant) for the hep-analysis boundaries, live run pending; `test_ams02_helpers.py` renamed
  `test_cosmic_ray_helpers.py`; a worked cosmic-ray spec with backgrounds and an active mask
  (`assets/worked-spec.cosmic-ray.synthetic.json`); the flagship example documents the `--profiles-from`
  validation command; capability-matrix title no longer carries a version.
- **Backgrounds and blinding in both journey examples (P4-2, P3-12).** `examples/collider-angular` subtracts a
  synthetic tau-pair-like background estimated from an x_vis sideband (transfer factor from the simulated shape, 10%
  fully correlated), closes it in a validation band and by Asimov, and blinds the forward signal-region bin
  cos theta >= 0.9 (outside the fiducial range). `examples/ams-flux-ratio` subtracts a synthetic Z=1 charge tail from
  the helium window with a charge-sideband estimate and validation band, and blinds the helium signal-region count at
  60-100 GV (helium flux, He/p ratio and period average null there; dataset records stop at 60 GV). In both, a
  custodian step runs `mask_blinded_bins.py` (the unmasked histogram lives only in a temporary directory), the
  unfolding fills the blinded bin with the simulated expectation at zero variance, figures pass
  `core.blinding.check_figure`, and the specs declare backgrounds, the transfer-factor systematic and the mask. The
  example tests check the estimate, the closure, the absent bins, and rerun with a synthetic sentinel in the blinded
  bins: outputs byte-identical, `audit_blinded_outputs.py` passes, a planted sentinel fails. The synthetic-collider
  profile generator gains an optional background sample with a visible-energy fraction (`generate_background`,
  `signal_xvis`, `xvis_fraction`, `--background`); `generate()` is unchanged. The published-comparison record copied
  from Path B is regenerated (its covariance gains the transfer-factor block).

### hep-statistics

- **Statistical-result hardening (contracts 2.6.0).** New errors: `stats.coverage_cl_mismatch`,
  `stats.coverage_interval_inconsistent` (a recorded interval outside the 99.73% Clopper-Pearson interval of its toy
  counts), `stats.p_zero_without_bound`, `stats.p_out_of_range` on probability-like `results` keys (p0, p_value, CLs,
  CLb, ...), `stats.z_p_inconsistent` (one-sided, |Δz| > 0.01), `stats.global_z_above_local`,
  `stats.construction_statistic_mismatch` (for example Feldman-Cousins with q0, CLs values from a Neyman
  construction), `stats.model_sha256_malformed`. New unresolved: `stats.coverage_toys_too_few` (fewer than 200 toys),
  `stats.expected_bands_missing` (an observed limit without median and both bands), `stats.global_z_without_p`,
  `stats.seed_missing`, `stats.gof_toys_missing`; Bayesian `stats.propriety_unsupported` (propriety needs
  {argument, ref}), `stats.poi_prior_missing`, `stats.ess_too_low` (100 per chain), `stats.chains_missing`; `stan`,
  `pymc`, `numpyro` count as gradient samplers and `uniform(0, inf)` as improper. Optional fields `extension.seeds`,
  `coverage.seed`, `goodness_of_fit.p_value_bound`, `significance.convention` (`ext_statistical_result_v2_6.json`).
- **Publication gate.** A `synthetic` or `asimov` statistical-result now fails (`gate.not_observed_data`); toy
  undercoverage is judged on the 68.27% Clopper-Pearson upper end computed from the counts; a blank backend or model
  reference is missing provenance. Gate verdict changes on committed artifacts: the J9 example
  (`examples/ml-classifier-to-inference`, `synthetic`) passed and now fails; 11 synthetic or asimov examples and
  fixtures go from unresolved to failed for the same reason; default and strict validator outcomes are unchanged
  for all of them (`tests/contracts/test_gate_verdict_snapshot.py`).
- `migrate_statistical_result.py` brings a 2.2-2.5 artifact to 2.6.0 (version only) and refuses one that breaks a
  2.6.0 error rule; it never repairs a number or invents a seed.
- **Comparison gate.** `variable-change` needs `edges` (the image of every current edge, strictly monotonic,
  recorded as `edge_map`) and a Jacobian that is a number or `{expression, ref}` (a bare word leaves the comparison
  unresolved); `from == to` is refused (use `rebin`). `unit-conversion` needs a finite factor > 0, recorded as
  `recorded_factor`. `plan_combination` refuses duplicate dataset ids (`combine.duplicate_id`); `envelope` refuses
  rows of unequal length.
- **`validate_covariance.py`** judges PSD, rank and conditioning on the correlation matrix D^-1/2 C D^-1/2: an
  indefinite correlation structure fails whatever the units per bin, and disparate but uncorrelated variances are no
  longer rank-deficient or ill-conditioned; metrics report scaled and unscaled eigenvalues.
- **`likelihood_limits.py contour`**: probes where a bin mean is <= 0 are out of the domain (q = +inf, counted as
  `out_of_domain_probes`), not failed fits; the 3-bin audit input now exits 0.
- **`result_artifact.py`** refuses a CLI output without `status` unless `--assume-status` is given (recorded as
  `results.cli_status_assumed`), refuses a coverage value or toy count under `--coverage-check not-checked`, and
  refuses a JSON list input.
- **Skill entry point and guide.** `SKILL.md` has a Step 0 for one-number questions and a task-to-tool table
  (default tool, fallback, or "no shipped tool"); the closure invariant applies to new models; the context stanza
  sits below Resources; the description says "producing missing physics inputs". `core-stats-guide.md` is split into
  a decision guide (conventions, a per-subcommand caps table checked against the code, choosing a tool, skill
  scripts with NumPy/SciPy markers) and `core-stats-commands.md` (per-module reference, gate rules). D'Agostini
  routes to `unfold-scan` (not `regularized-scan`, which refuses it). Ten reference corrections with ledgered
  sources (Bartlett's effect, `SumW2Error` scope, code4p sign convention, pyhf zero-nominal and staterror defaults,
  iminuit EDM, familywise global p-values, ROOT 6.40 off the Combine stack, ...). New
  `assets/combine.example.json`.
- **New capabilities.** `covariance_fit.py`: broken and smoothly broken power laws, plug-in models, `break-scan`
  (toy-calibrated break interval and no-break test); `statistical_toys.py ratio-cov-analytic` (full ratio
  covariance at counts >= 1e4); `unfolding_diagnostics.py dagostini-unfold` (data unfolding with data and response
  covariance); `shape-limit` without toys at ordinary sizes (100 bins, 1e4 events per bin); `shape-significance`
  (multi-bin q0).
- **Defects fixed on valid inputs.** Exact Phi quantiles for expected bands (`cls-limit --n 2 --b 3.7`: -2 sigma
  2.996, was 3.56; `profile-cls` too); MC ranges for `profile-cls` and `profile-limit`; `shape-limit` at n = 0,
  b = 0 (boundary, no longer failed) and a toy-CLs runtime estimate with a 600 s budget; `unbinned_fit.py` at wide
  or offset ranges (natural-scale Hessian steps, exponential relative to lo, boundary policy for n_sig);
  `eft_scan.py` excludes nu <= 0 in empty bins and refuses CL outside (0, 1); `global_significance.py` input checks,
  auxiliary redraw at the fitted scale, shared upcrossing definition; `pcl_efficiency_ratio.py` exact classical limit
  (n, b up to 1e5 in < 1 s); `covariance_fit.py` checks `relative_cov`; `look_elsewhere.py` memory budget;
  `sensitivity_and_gof.py` reports an infeasible model; `model_card.py` leaves validation regions out of the fit and
  uses constraint widths. Every statistics CLI refuses malformed input with exit 2 and JSON (no tracebacks) and
  prints `--help` without NumPy.
- **References.** `unfolding.md` (SVD, TUnfold, iterative and fully Bayesian unfolding, OmniFold, purity and
  stability, undercoverage of regularized intervals, publishing), new `combinations.md` (BLUE, negative weights,
  Peelle's puzzle, likelihood-level combination), `inference-recipes.md` (Wald and sigma_A, Rolke-Lopez-Conrad,
  Cousins-Highland, PCL, the conditional on/off test, Baker-Cousins, reference priors), `nuisance-modeling.md`
  (`autoMCStats`, spurious signal, discrete profiling, non-additive breakdowns), `astroparticle-statistics.md`
  (unbinned point-source likelihood, TS and Chernoff, Rayleigh/Z_m^2/H-test, Bayesian blocks). Every new source is in
  `docs/evidence/statistics/sources.json` with its verification level (S15-S41), with claims C12-C17 and eight new
  capability entries.
- **Routing checks are language independent** (all skills): `tools/check_routing_static.py` requires trigger terms
  for English cases only; a non-English case may be a natural prompt (`"natural": true`) that reuses no four
  consecutive description words; the description-topics table in `docs/routing-contract.md` (hep-statistics row
  now) must stay named in the owner's description. New cases: six natural zh-Hant hep-statistics prompts, ratio
  with covariance, broken-power-law fit to published points, bump hunt with a fitted background, an English
  combination prompt, and the fit half of J5 (`j05-turn-fit`, Q9).
- `examples/ml-classifier-to-inference/run.py` records the coverage toy seed and no longer crashes on an unresolved
  finding (`Finding.severity`, not `.level`); J9 and `published-comparison` outputs regenerated (version strings,
  the seed, the schema list read).

### Integration (PR #64)

- **Same-event systematic variations.** `check_systematic_variations.py` no longer combines per-sample variances
  (ROOT bin errors, JSON `*_sumw2`) as if the variation were independent of the nominal: that hid a 3% JES shift made
  from the same events (`none`, "neither variation changes this histogram"). The statistical test now uses
  `up_diff_sumw2`/`down_diff_sumw2` (new), `--stat-unc`, or per-sample variances only with `--independent` (new);
  otherwise no test is made, the output says why, and the effect comes from the tolerance. The "neither variation
  changes" warning is given only when no bin changed. When bins differ but neither variation is flagged, the
  warning says "not significant at alpha" only if a statistical test was made; on the tolerance-only path (including
  same-event variations without difference variances) it says the integral and normalized shape stay within the
  tolerance, and the per-variation note no longer claims that no bin differs.
- **`check_root_cpp_env.sh` under `set -e`.** A nonzero exit of `root --version` (informational) ended the check
  without output (CMP-08 moved it into an assignment); it is now tolerated, and a failing `root-config` reports
  `failed` in the JSON. Found by the optional ROOT CI job (Linux container), whose check-run record is now uploaded.
- Test fixes found by CI: the pyhf skip restored on `SrCrModelCard`; the broken-power-law covariance comparison uses a
  relative tolerance (finite-difference precision, Python 3.11).

### hep-statistics follow-ups

- **One broken-power-law parametrization (STH Q8).** New helper `core/stats/broken_power_law.py` (steward
  hep-statistics, no CLI): `[ln A, gamma1, gamma2, ln x_b]`, `ln F = ln A - gamma1 (u - h) - gamma2 h`,
  `u = ln(x/x_b)`, `h = max(u, 0)` (sharp) or `s ln((1 + e^(u/s))/2)` (smooth), so `A = F(x_b)` in both forms.
  hep-analysis `cr_spectrum_powerlaw_fit.py` and hep-statistics `covariance_fit.py` both evaluate it and give
  identical model values. Behavior change in `cr_spectrum_powerlaw_fit.py --model smooth-broken`: its smooth form
  lacked the 1/2, so the reported `normalization_at_break` was `F(x_b) 2^((g2-g1) s)`, not the flux at the break; it
  is now `F(x_b)` (indices, break and chi2 unchanged). Documented once in the core/stats guide (conventions) and
  linked from the hep-analysis guide; the guide's stale "diagonal errors only" description of
  `cr_spectrum_powerlaw_fit.py` is replaced.
- **hep-statistics SKILL.md headroom.** 8178 -> 7653 B (budget 8192): the Resources list of ten reference links moved
  into a reference index in the core/stats guide (Contents), with the ML-assisted link kept in SKILL.md; the
  "N hypotheses, no scan data" row (Bonferroni or Sidak, by hand, labeled) moved to the guide's Choosing a tool table.
  No rule removed; the description and the generated context-resolution stanza are unchanged. The guide stays under
  its 17000 B test (16944 B) by dropping a sentence that repeated its "run, do not hand-compute" convention.

## 0.6.17 (2026-10-13)

Contracts 2.5.0 (minor: ML semantics; every 2.4.0 artifact keeps its outcome and gets the new rules with
`validate.py --strict`; no new capability).

- **ml-artifact semantics (contracts 2.5.0).** `ext_ml_artifact.json` gains optional `splits.overlap_check`,
  `splits.manifest`, `splits.test_groups_disjoint`, an object form of `weights` (source, negative-weight treatment,
  class balancing, where the weights are used), `domain_shift`, `environment` and `output_semantics`. New checks
  (native from 2.5.0): blank grouping key, empty model hash, labels or features, training-domain keys outside the
  features or with lo >= hi, a failed split-overlap check, calibration missing for probability or density-ratio
  outputs or for inference, calibration evaluated on its fit sample, or incomplete are errors; an overlap check not
  run, a missing or failed domain-shift check on a model with downstream use are unresolved; no overlap check,
  dropped negative weights and missing seeds are warnings. New `scripts/write_ml_artifact.py` builds and validates
  the artifact from a training run summary, calibration, domain-shift and split-check results.
- **physics-ml: the invariants are enforced in code.** New `scripts/make_grouped_splits.py` (by run, period, seed or
  parameter point; random-groups, temporal or k-fold; null groups refused unless a policy is given; its manifest
  passes `check_split_integrity.py`). `assets/train_classifier.py` trains from a data file with `--split-manifest`,
  runs the split check first and refuses a leaky split, uses signed event weights in the loss and the metrics
  (training and evaluation weights recorded separately), selects on validation and reports a test split used once,
  stores features, units, standardization and the training domain in the checkpoint, and writes a run summary and
  validation and test scores. `assets/inference.py` checks feature names, applies the stored preprocessing and flags
  (or with `--on-out-of-domain reject` refuses) inputs outside the training domain. New `assets/calibration.py`:
  temperature, Platt and weighted isotonic calibration, weighted reliability curves, ECE with its finite-sample floor,
  fit and evaluation samples required to be disjoint. New `assets/set_classifier.py`: Deep Sets/PFN and a ParT-lite
  with masks, ragged collation, phi wrapping and permutation, padding and empty-set tests.
- **physics-ml: domain check rewritten.** `check_surrogate_domain.py` whitens the inputs and uses Mahalanobis and
  k-nearest-neighbour distances with thresholds calibrated as quantiles on held-out training points, and reports the
  false-positive rate. The per-feature box is a diagnostic only (`--box-strict` restores it as a criterion). The old
  check called a 20-dimensional extrapolation (Mahalanobis 9.3) inside and could call an in-distribution point
  outside; `--factor` is removed. Constant features no longer overflow, a dimension mismatch is an input error (exit
  2) and numerical failure exits 3.
- **physics-ml: fixes.** `check_split_integrity.py`: a null group is reported (it used to pass) and ids and groups
  are compared after stripping and case folding (`--case-sensitive` to opt out). `compare_model_runs.py`: the
  command-line `--lower-is-better` wins over the runs file. `metrics.py` refuses shape mismatches that broadcast;
  `transformer_classifier.py` gives finite outputs for fully masked rows; `last.pt` records the current best value;
  `vision_transfer.py` keeps a frozen backbone's BatchNorm in eval mode; `torch.load` uses `weights_only=True`; every
  PyTorch asset answers `--help` without torch (exit 3 when run without it). `train_classifier.py`: `--use-amp` is
  replaced by `--precision fp32|bf16|fp16`, `--num-classes` defaults to 2, `config.yaml` is read with `--config`.
  `inference.py` takes `--input CSV` and reads the model shape from the checkpoint.
- **physics-ml: references updated.** Grouped splits replace row-level `random_split` in the examples; bf16 and fp16
  in one mixed-precision file with the fp16 range warning for inputs in MeV, keV or ADC counts; FSDP2 and distributed
  checkpointing; ONNX export with `dynamo=True` and `dynamic_shapes`, `torch.export` and AOTInductor, TorchScript no
  longer recommended; checkpoints save RNG, GradScaler and sampler state with an atomic write; deterministic
  algorithms and worker seeding; `torch.compile` with dynamic shapes for variable multiplicity; each code section
  states the torch version it was run with. The PyTorch guide routes to the physics references and no longer tells
  BDT questions to skip them. Generic serving, monitoring, fine-tuning and large-model material is labelled as such
  and LLM-only passages are cut; `assets/scaling-plan.example.json` (a 7B plan) is removed and
  `dataset-splits.example.json` uses runs.
- **Routing.** The ownership table gains ML rows (BDTs and classical MVA, ML-assisted inference training, fast
  simulation training, calibration of model outputs to physics-ml; inference coverage to hep-statistics; detector
  calibration and fast-simulation validation to detector-response). detector-response hands learned fast simulation
  and ML response models to physics-ml; hep-analysis hands classifier or BDT training to physics-ml. Eight routing
  cases (en, zh-Hant) for BDTs, negative weights, working points and an ECAL regression.
- **Worked example (journey J9).** `examples/ml-classifier-to-inference/`: see VALIDATION.md. The synthetic-collider
  profile lists physics-ml.

- **physics-ml: HEP content and task routing (external review patch).** `ml-analysis.md` becomes the physics entry
  point (23 to about 290 lines, original content kept): grouping and k-fold, training versus evaluation weights, class
  balancing and prior correction, four treatments of negative weights and the optimization pathology, analysis
  metrics (background rejection at fixed signal efficiency, Asimov significance with background uncertainty), mass
  sculpting and decorrelation (DisCo, adversarial, planing, DDT, MoDe), parameterized and systematic-aware training,
  simulation-to-data (scale factors, DCTR, domain-adversarial), weak supervision (CWoLa, CATHODE, CURTAINs), the
  OmniFold training side, and deployment in experiment frameworks and triggers. New references
  `particle-and-jet-architectures.md` (Deep Sets/EFN/PFN, ParticleNet, ParT, LorentzNet/PELICAN, variable
  multiplicity, a masked Deep Sets example with permutation and empty-set checks), `fast-simulation-validation.md`
  (conditioning range as training domain, physics constraints, five metric classes, statistical meaning of generated
  samples), `space-and-astroparticle-ml.md` (methods only; experiment facts stay in the profile) and
  `sbi-training.md` (NRE/NPE/NLE training, diagnostics handed to hep-statistics). `multivariate-analysis-bdt-nn.md`:
  XGBoost has raised a fatal error on negative weights since 1.3.0 (it said "can silently mishandle");
  `generative-models.md` points to the fast-simulation file and flags BCE and FID as unsuitable for physics data.
- **physics-ml: weighted metrics and losses.** New `assets/hep_metrics.py` (NumPy, also a CLI with strict JSON):
  signed-weight ROC/AUC, weighted efficiency with MC statistical uncertainty, 1/eps_B at fixed eps_S (a lower bound
  when eps_B <= 0), Asimov significance with sigma_b, N_eff, weighted squared distance correlation, mass-sculpting JSD
  with a statistical baseline, prior correction. New `assets/hep_losses.py` (PyTorch): signed-weight BCE with three
  normalizations, per-batch weight report, DisCo penalty (float32, finite gradient on constant-score batches),
  NaN-safe masked softmax and mean. 33 tests against analytic or construction-known values (Gaussian AUC,
  Mann-Whitney with ties, integer weights equal duplicated events, Asimov limits, dCor cases, sculpting detection);
  the PyTorch tests ran with torch 2.14.1 on CPU.
- **physics-ml: description and routing.** The description is written by task and includes BDTs in analyses, adds
  the load-first clause and a detector-response Not-for; an invariant records training and evaluation weights
  separately; Resources becomes a task-to-reference table; Handoffs gain a hep-analysis row and widen the
  detector-response row to scale factors and tag-and-probe.
- **Profiles connected to physics-ml.** AMS-02 lists physics-ml in `related_skills` and its working-rules routing
  table gains a classifier/regressor row; the EIC profile lists physics-ml and its placement inventory gains an ML row.
- **Partition engine: retries bounded across runs (hep-computing audit F01).** `core/partition/engine.py` counted
  `max_attempts` per `run()` call, so rerunning bought new attempts (3, 6, 9, 12 over four calls). Attempts are now
  counted since the chunk's last `reset()` over all calls (`attempts_since_reset`, as in the batch campaign); a chunk
  with none left reports `attempts-exhausted`, and only `reset()` with a reason restores the budget. The "two identical
  failures stop" rule compares failure signatures instead of raw messages: `local_partition.py` gives each command
  failure a stable signature (exit code, timeout, missing or invalid output), and other exceptions are compared with
  paths, long hex strings and numbers masked. `max_attempts` must be an integer of at least 1. A state written before
  this change counts all its recorded attempts (fail closed).
- **Partition engine: merge reads canonical chunk files only (F02).** `merge()` took chunk files in filename order and
  kept the first claiming a chunk, so a stray `b_c0000.json` with another result replaced `c0000.json` and the merge
  still reported `complete`. Each chunk is now read from `chunks/<id>.json` only; a stray file with the same result is
  reported (`merge.duplicate_chunk`), one with a different result makes the merge incomplete
  (`merge.conflicting_duplicate`), and a stray never stands in for a missing chunk. New hard problems
  `merge.id_mismatch` and `merge.seed_mismatch`; non-object or incomplete chunk files are reported as
  `merge.unreadable` instead of crashing. Regressions: `tests/core/test_partition_p0_regressions.py` (15 tests, 14
  fail on the previous code).
- **`local_partition.py`: missing-output message names the path.** The new `missing-output` failure printed
  `{out}` literally (missing f-string prefix).
- **`run_all_checks.py` runs test modules in parallel by default.** `--jobs` defaults to the CPU count, at most 8
  (was 1); `--jobs 1` runs them serially. Each module already ran in its own process; the full suite passes with
  `--jobs 8` (5 min 54 s wall time on an 8-core host).
- **CI runs faster without testing less.** `tools/run_all_checks.py` starts test modules slowest first (durations
  in the new `tools/module_timings.json`), gains `--part units|checks` and `--shard K/N` (shards balanced by those
  durations; every module in exactly one shard) and `--write-timings`. The `checks` job of `tests.yml` runs as three
  parallel jobs per Python version (two unit shards, one for the profile suites and static checks), and the optional
  jobs use the parallel runner instead of a serial `unittest discover`. `tools/check_ams_optional.py` runs its suites
  one test module per process with `--jobs` (the same modules as `unittest discover`; 218 s to 66 s locally with 8).

## 0.6.16 (2026-10-13)

- **detector-response: front-end electronics and signal processing.** New reference
  `front-end-electronics-and-signal-processing.md` models readout electronics as part of the response: signal
  induction (Shockley-Ramo, ballistic deficit), shaping, noise (series, parallel, 1/f, leakage-current scaling,
  correlated noise in sums, common mode), thresholds (S-curves, Rice noise-hit rate), optimal filtering and sampling,
  ADC/TDC quantization and nonlinearity, time pickoff (jitter, walk, CFD modes), pileup (Campbell, bipolar baseline
  transients), dead time and live fraction, SiPM and PMT readout, LAr TPC signal processing, radiation effects,
  calibration and simulation of the electronics, with an explicit out-of-scope list (circuit, ASIC, FPGA design).
  New script `frontend_response.py` (ENC with closed-form CR-(RC)^n integrals and the shaping optimum, noise-hit rate,
  timing, quantization, pileup, SiPM, ballistic deficit, dead time, cluster noise), each result with a validity list;
  23 tests against values checked by numerical integration and Monte Carlo. The bibliography gains an electronics
  section of nine Crossref-checked citations (Shockley, Ramo, Radeka, Spieler, Cleland-Stern, Rice, Vinogradov,
  MicroBooNE signal processing, Moll).
- **detector-response: electronics statements corrected.** Shaping trades series against parallel noise (an optimum,
  not "slower is quieter"); sub-Nyquist sampling with a known pulse shape is unbiased; optimal filter instead of
  "template fit is best"; common-mode estimates exclude signal channels; dead-time formulas are exact for Poisson
  arrivals and the paralyzable form is given; photostatistics timing `tau_d/N_pe` rather than `tau/sqrt(N_pe)`; clock
  jitter split into global and local parts; the reference time dominates in low-multiplicity, not busy, events;
  `LSB/sqrt(12)` needs dithering noise; dark counts add variance, not only an offset. `triggers-luminosity-pileup.md`
  gains a dead-time and live-time section (the existing cross-reference had no target), and the effective luminosity
  is summed per block with its live fraction.

## 0.6.15 (2026-10-13)

Contracts 2.4.0 (minor: response semantics; every 2.3.0 artifact keeps its outcome and gets the new rules with
`validate.py --strict`; no new capability).

- **Response validation by intended use, and a correct counts closure (detector-response review WP1).**
  `core/stats/validate_response.py` folds a `counts` closure through `M_ij / generated_j` (it multiplied the raw
  counts, 100x off in the review case) and reports it `not_assessable` without `generated_per_truth_bin`. A new
  `metadata.intended_use` (`forward_folding`, `unfolding`, `parametric_fit`) sets the identifiability verdict:
  `underdetermined`, `rank_deficient` and `empty.truth_bin` stay errors for `unfolding` and when the use is undeclared
  (with a new `metadata.intended_use_missing` warning), and are warnings for the other uses. Closure now runs unless
  shape, entry, normalization or orientation errors block it; `conditional_on_selected` with acceptance inside the
  matrix and negative closure truth are errors. Rewritten tests: `test_empty_truth_bin`,
  `test_degenerate_truth_bins_are_not_identifiable` and `test_fewer_reco_than_truth_bins` declare `unfolding` and also
  check the undeclared case.
- **Response artifact semantics and adapter (Contracts 2.4.0).** For 2.4.0 artifacts (older ones with `--strict`),
  `includes` / `applied_separately` use the `response_corrections` vocabulary (every `<x>_efficiency` counts as an
  efficiency, so `trigger_efficiency` no longer bypasses `response.double_counted`); a matrix needs `matrix` or
  `matrix_ref` (`response.matrix_missing`); `conditional_on_selected` with inefficiency or acceptance inside and
  `joint_counts` with inefficiency inside are `response.normalization_inconsistent`; one variable in two units is
  `response.unit_mismatch`; unknown terms are `response.unknown_correction`. Optional `matrix`,
  `generated_per_truth_bin`, `intended_use` and `variable_conversion` fields. New `contracts/response_adapter.py`
  converts a response artifact into validator input (explicit errors for unmappable values such as `unnormalized`) and
  folds through it; the collider-angular and ams-flux-ratio examples use it instead of a second hand-written
  declaration. The folding reference writes `nu = D_reco R D_truth x + b` with each correction's space and order.
- **PID scripts guard their validity ranges (WP2).** `pid_separation_power.py` passes the species charge to
  Bethe-Bloch (d/He4 at 2 GeV/c: 121.6 sigma, was 17.9), takes `--rigidity`, refuses beta*gamma < 0.1 instead of
  returning a negative dE/dx, reports every `below_threshold_interval` (crossing dE/dx bands) with
  `ceiling_is_lower_bound`, and labels `separation_convention` / `reference_species` (`--convention single|quadrature`).
  `cherenkov_angle.py` reports `expected_photons`, `p_no_photon` and `photon_regime` and gives no Gaussian separation
  with fewer than 5 expected photons; `--track-resolution` adds a term that does not shrink with N (default 0 keeps
  the values); field `detected_photons` renamed `expected_photons`.
- **Script outputs are valid and labelled (WP3).** Every detector-response CLI emits strict JSON or a JSON error
  (no NaN, Infinity or traceback). `tag_and_probe_efficiency.py` keeps the 0.95 default but renames its fields
  (`interval_level`, `lower_bound`/`upper_bound`, `distance_to_lower_bound`/`distance_to_upper_bound`) and returns
  nulls with a reason for zero probes (rewritten test: `test_efficiency_bin_zero_total_is_null_not_error`).
  `pileup_reweight.py` reports `n_eff` and `max_weight` with warnings and fails on non-finite weights; the calorimeter
  fit takes per-point uncertainties, reports the covariance, an ndof warning and `extrapolated`; multiple scattering
  warns outside the Highland range; Gaisser-Hillas adds the standard shower age and evaluates in log space.
- **Reference corrections (WP4).** Sixteen review items in the detector-response references: the tracking resolution
  minimum is not at the crossover, `1/(B L^2)` scaling with the Gluckstern terms, the energy-scale flux shift is
  `(gamma - 1) * delta`, muon excess of heavy nuclei by sublinear superposition, per-period simulation instead of
  time-averaged conditions, truth-matching efficiency is not exact, charge confusion is a tail property at every
  rigidity, and others; N_sigma (both conventions), purity, fake and duplicate rates and width estimators are defined
  once in the performance-metrics reference; new approximate formulas carry their PDG source.
- **detector-response SKILL.md (WP5).** A stop rule when the inputs cannot determine the answer, the intended use in
  every response declaration, handoffs for a hep-theory prediction to fold and for tag-and-probe fits and pileup
  systematics to hep-statistics, and a task-routing table in the principles summary (SKILL.md 7266 B).

- **Skill READMEs and trimmed entry points.** Every skill folder has a `README.md` (purpose, folder map, scripts,
  references, handoffs, tests) linked from the plugin README and from each `SKILL.md`. The detector-response,
  hep-statistics and hep-computing `SKILL.md` files, which sat at the 8 KiB budget, keep their rules and point to new
  index sections in the principles summary, the core/stats guide and the engineering playbook for the reference and
  script lists; a live routing rerun of the 80 cases involving them scored 75 of 80 with no change attributable to the
  trim (VALIDATION SKILL-TRIM).
- **Live behavioral evaluation recorded.** `evals/research_communication/run_live_eval.py` runs the eleven cases through
  a headless `claude -p` with the routing harness's isolation; one run on claude-sonnet-5-5 at 0.6.14 (`f7709da`,
  $0.71) scored 6 pass, 4 fail (all routing: quick cases answered without a plugin skill) and 1 critical-fail (a
  referee reply asserting an edit behind a bracketed caveat); no fabricated evidence, invented number or status
  promotion. The scorer was calibrated to 1.1 on that run (grounded fixture content, file:line references, years,
  negated phrases, phrase alternatives); the semantic judgments are the executor's, not an independent review.

## 0.6.14 (2026-10-13)

- **Lint-clean contracts.** No behavior change from 0.6.13: the communication contract modules satisfy ruff (B007)
  and mypy as the CI lint job runs them (an unused loop index; four `isinstance` narrowings written so mypy sees
  them), and the research-communication scripts drop three unused loop variables and chain one exception. The 0.6.13
  tag failed the lint job on GitHub after its push; this release carries the fix.

## 0.6.13 (2026-10-12)

Contracts 2.3.0 (minor: the capability `communication:traceability-v1` and its extension schema; every 2.2.0 artifact keeps its outcome). `contracts/migrate_statistical_result.py` now writes the current contracts version (2.3.0) instead of a literal 2.2.0; the 2.2.0 rules it applies are unchanged.

- **Research-communication review minors closed.** A ```latex fence counts as a diagram only when it holds a
  `tikzpicture`, so `check_diagram_sources.py --require-render` can pass on a bundle of code examples; a changed
  document digest is unresolved (not a warning) when any of its occurrences is marked inspected; a revision edge whose
  value matches the recorded display never erases a value change found on another edge; revision and adaptation
  reports are ordered independently of the hash seed (the worked example no longer pins `PYTHONHASHSEED`); the legacy
  `sources_read[].id` is any non-empty string again (the traceability format keeps the namespaced id); a claim whose
  edges are all context-only is held to the envelope statuses and reported as unmapped; `check_manuscript.py` tries
  `name.tex` then `name` for an include and, in `--main` mode, `--style` scans only the included files; a literature
  re-import with a different DOI or arXiv id for the same local id is an identifier conflict (the record keeps its
  value) and an alias merge keeps the incoming arXiv version in the history; `score_replay.py` exits 3 when no output
  matched a case.
- **Communication traceability (research-communication reliability plan, T1).** Legacy `communication` claims are
  typed: `text` and `result_ref` are non-empty strings and `status` a core status or an array of them (a numeric text,
  a null reference or an object status used to pass). A new reader capability `communication:traceability-v1` selects
  `contracts/schemas/ext_communication_traceability.json`: claims with stable ids, evidence edges (`artifact` targets
  matched to `inputs[].ref`, `source` targets to a declared or bound evidence ledger; locator, role, `usage`),
  document occurrences, read events and support assessments. `contracts/communication.py` applies the pure rules: a
  claim inherits the sticky caveats of every `used-in-claim` edge whatever its role (a `contradicts` edge is no
  escape), carries `observed` only with an observed or source edge, never `observed` with `synthetic`/`asimov`, and an
  assessment is bound to a digest of the claim text and scope and to the input digests (a wording change or a changed
  hash makes it stale and unresolved; `currency: current` on a stale assessment is an error). The envelope rules are
  unchanged: the envelope keeps the sticky caveats only, so a mixed observed/synthetic document is representable. The
  marker `traceability_version` without the capability, an unknown version, or the capability without the marker are
  errors; a 2.2.0 reader without the capability refuses the record. `contracts/communication_project.py` resolves a
  record inside a project root through `contracts/dependencies.py` (which gains an additive `vocab` parameter so
  sources using a bound profile's terms validate), loads declared and bound-profile ledgers, resolves source ids and
  document digests, and normalizes outcomes (`resolve_outcome`: input-error 2, fail 1, incomplete 3, pass 0;
  unresolved findings or a failed upstream never read as complete). A legacy record is reported as limited
  traceability. Contracts move to 2.3.0 with this release (additive: a new capability and schema; no field removed or tightened for 2.2.0 artifacts).
- **Manuscript checks scoped to the selected document (T2).** `check_manuscript.py --main MAIN.tex` scans only the
  files the main document reaches through literal `\input`, `\include`, `\subfile` and `\import`, resolved against
  `--build-root` (default: the main file's folder) and bounded by `--project-root`; a label in an unincluded sibling no
  longer satisfies a reference, and two documents in one folder may share labels. Only the bibliography the document
  declares counts; a built `.bbl` counts only with `--bbl`, otherwise the citations it alone could resolve are
  unresolved (exit 3). Macro-generated names, conditional includes, `\includeonly`, missing includes or `.bib`
  files, out-of-root paths and include cycles are reported as incomplete coverage (exit 3), never guessed. Verbatim
  and listing bodies are ignored. Directory mode is unchanged and labeled a repository-wide source scan, except that an
  empty directory is now a no-input error (exit 2) instead of "No issues found". `--format json` prints one report
  object (report_version 1.0.0: status, exit code, coverage, checks run and not run, findings with codes).
- **Diagram verification coverage reported honestly (T3).** `check_diagram_sources.py` gives every block one outcome:
  `rendered` (nonempty renderer output), `lint-only` (Mermaid structural lint without `mmdc`; SVG XML
  well-formedness), `skipped` (DOT without `dot`, PlantUML without `plantuml`, TikZ/LaTeX, which it never compiles),
  `source-error` or `environment-error` (not started, timed out, startup failure, exit without output). Each renderer
  gets one preflight; one that fails it, or times out on a block, is not launched again. Counts reconcile with the
  total; "Checked N block(s)" no longer counts linted or skipped blocks as verified, and rendering is reported apart
  from visual inspection, which the checker never performs. Exit codes: 1 source error; 3 environment error, or with
  `--require-render` any block that was not rendered; 0 otherwise (a timeout used to exit 1 as if the source were
  wrong). `--format json` prints the per-block outcomes, renderer availability and versions.

- **Handoffs and instruction semantics aligned (T4).** `code-review-report.md` and the papers guide now route by the
  question asked, not by the library: implementation, I/O and performance to `hep-computing`, measurement design and
  corrections to `hep-analysis`, statistical treatment to `hep-statistics` (also in ROOT or uproot code), ML rigor to
  `physics-ml`, theory validity to `hep-theory`, detector response to `detector-response`; the old text sent
  statistical treatment of ROOT/uproot code to `hep-analysis` and reruns to `hep-analysis`/`physics-ml`. The 3σ/5σ
  significance table in `scientific-style.md` is scoped to a search's significance statement under the source's own
  field convention; the everyday sense of "evidence" carries no threshold. `citation-verification.md` defines reuse
  of previously verified records (dates, versions, read levels and locators kept; a recheck is a new read event
  beside the old one, never a relabeling). `submission-and-peer-review.md` ties response wording to the revision
  ledger: "we have changed" only for a completed, checked change; pending reruns stay explicit. Six routing cases
  cover these handoffs (`tests/routing/cases.json`, 157 cases) and `test_handoff_text.py` pins the sentences.
- **Results linked to claims; reporting completeness (T5).** Two new research-communication scripts.
  `check_communication.py RECORD --project-root ROOT --checks schema|traceability|manuscript` validates the record,
  resolves its inputs, ledgers, sources and documents, and with `manuscript` opens each declared document and
  compares every declared occurrence with the current text at its locator (Markdown headings; LaTeX sections,
  environments and labels), so a correct manifest cannot mask a wrong manuscript sentence; coverage counts
  (declared, located, checked, mismatched, unresolved) are reported and whole-manuscript coverage is never claimed.
  `audit_claims.py` checks recorded assessments (an unsupported verdict is a confirmed inconsistency), source read
  coverage (a passage cited beyond what the read event covers is unresolved: an abstract value is citable with the
  abstract locator, an unread table is not), advisory wording (status promotion, discovery wording without a global
  significance, generalization beyond the recorded scope; quoted, negated and attributed sentences are skipped),
  display values against exact source values under the occurrence's declared rounding (no invented tolerance; an
  undeclared rounding is a review candidate, an unrecorded unit conversion unresolved), and reporting completeness
  against `assets/reporting-policies.json` (measurement, search, limit, theory prediction, ML result; conditional on
  supplied method metadata, never a chosen default: an expected limit does not imply Asimov, a Bayesian interval
  needs no frequentist construction). It emits a claim matrix, draft-ready facts and handoffs to the producing skill.
  Both print one JSON report (report_version 1.0.0; markdown is a view), refuse an output path that aliases an input,
  and use the exit precedence input-error 2, fail 1, incomplete 3, pass 0. Every CLI consumes the full resolved
  context (schema, resolution and dependency findings), so a missing or replaced evidence file never passes a claim
  audit; an artifact locator that does not resolve is unresolved; read coverage matches whole locators (`Table 1`
  does not cover `Table 12`); a claim waiting on declared inputs, a manuscript check without occurrences, and an
  occurrence whose LaTeX region includes other files are unresolved, not pass or fail. Reference: `evidence-linked-writing.md`.
- **Revision impact and stale assessments (T6).** `track_revision_impact.py BEFORE AFTER --project-root ROOT` compares
  a baseline and a revised record through their pinned identities (input digests, evidence fingerprints, claim
  digests) and classifies each changed claim: analysis rerun (value at the evidence locator changed), source change
  (identity changed, value not shown to differ: reconcile, not reopen), reference move (same identity, new path),
  reassessment (wording or scope changed, sources unchanged), content edit (occurrence text or rounding only), status
  change, added, removed. Every recorded occurrence of a changed claim is listed as stale or edited (abstract, body,
  caption alike); the assessment is reopened where the evidence or wording changed and kept otherwise; a stale
  assessment is reported as needing re-inspection, never as false. A verified revision item that depends on a changed
  claim is reopened; one without completion evidence is an error; an edited item is not evidence that edits happened.
  The baseline is never modified and an old reference is never re-resolved against today's file: when the historical
  content is gone, the impact is reported at identity level with the baseline's own recorded display value, and the
  content comparison is marked incomplete. Each impact lists every change it carries (`changes`), so a rename plus
  stronger wording still reopens the assessment; the revised record's own findings are part of the report; baseline
  references are read only inside the project root and only with their pinned digest. Coverage is the recorded
  occurrences; the report asks for a targeted read of paraphrases instead of claiming whole-manuscript coverage.
- **Literature and citation lifecycle, offline (T7).** `manage_literature.py import INPUT.json --project-root ROOT
  --out OUTPUT.json [--into EXISTING.json]` imports evidence-ledger sources and claims, an explicit search log
  (database, interface, exact query, filters, date, coverage limits, export count, discovery route; template in
  `assets/paper/search-log-template.json`) and status notices into a new literature record with provenance (input
  path and digest, date). Records merge only on identical stable identifiers (DOI, arXiv id without version, INSPIRE
  record) and only across the same formal status; similar titles are proposed merges, never performed; a report and
  a study of one work stay related as same-work. An arXiv version change keeps the history and flags citing claims to
  reassess. A correction or retraction flags dependent claims (reassess inside the notice's scope, check outside) and
  deletes no citation; a journal-version notice records a supersession with its provenance. An old verification date
  is a recheck flag, never an error; an inaccessible full text is an access limitation. Citation keys are preserved and
  collisions reported. The input is never edited; no lookup is performed, and the record says online verification was
  not performed. Quoted instructions inside a source's notes are data.
- **Audience adaptation and evidence-backed reviewer responses (T8).** `check_adaptation.py RECORD --project-root
  ROOT --manifest M --draft D` checks a derived draft (paragraph, abstract, talk outline, poster, public summary;
  skeletons in `assets/paper/audience-adaptation-templates.md`) against its companion manifest
  (`assets/paper/adaptation-manifest-template.json`: brief with audience, format, budget, central claim, record digest
  and indispensable limitations; one statement per quantitative statement or conclusion with its claim ids; omissions;
  unresolved inputs; semantic review): a statement missing from the draft or without a claim id, a number that matches
  no recorded value, a dropped status label, a dropped indispensable limitation, or a universal wording whose claim
  scope is narrower is an error; a stale record digest or a missing semantic review is unresolved (keyword overlap is
  not a semantic check). `--responses` builds the reviewer action table (comment, claims, revision items and states,
  locators, completion evidence) and generates response wording from the recorded state: past tense only for a
  verified change with evidence, pending work explicit, a reasoned decline valid with its reason; a draft that asserts
  uncompleted work is an error.
- **Project terminology and notation consistency (T9).** `check_terminology.py RECORD --project-root ROOT --glossary
  G` scans the record's documents against a project glossary (`assets/paper/glossary-template.json`: concept,
  preferred term per language with English and Traditional Chinese, contextual aliases, definition, abbreviations,
  scope, disallowed substitutions with the context words that make them a likely confusion; notation definitions by
  section scope). Findings are contextual and carry both locations and the rule: a disallowed term next to its context
  word (warning; acceptance versus efficiency, resolution versus precision, confidence versus credible, in either
  language), an abbreviation redefined with another expansion (error) or used before its definition (warning), a
  symbol defined twice in one section with different wording (error), a definition in a scope the glossary does not
  declare (warning). Aliases, bilingual equivalents and declared scoped reuse are never flagged; quoted and
  "so-called" mentions are skipped; nothing is replaced or translated, and meaning stays the reader's review.
- **T17 toy construction diagnosed.** The published-likelihood benchmark (ATLAS-SUSY-2018-31 SRB) adds a post-hoc
  diagnosis, labelled as such: the exact counting CLs limit of the one-bin SRB (n = 3, b = 3.23) is 5.284, inside the
  toy limit's MC range; pyhf's toys match exact Poisson sums on the bare one-bin model; the asymptotic formulae give
  4.68 there, 12% below the exact limit. The toys are correct; the published 4.9 follows the asymptotic construction,
  which understates the limit at three events. The preregistered toy-vs-paper verdict stays a fail.
- **sci-fix: CLs crossings interpolate log CLs.** Linear interpolation of CLs between the 1.0-wide toy grid points put
  every toy crossing 0.06-0.12 too high (observed 5.34 -> 5.28, -1 sigma 4.03 -> 3.94); no verdict changed.

## 0.6.12 (2026-10-12)

- **Discrete profiling coverage established (T27).** A preregistered follow-up with 1,500 toys per envelope row
  (seed 20261013, criteria unchanged) passes bias and coverage for all four truths and both injected signals
  (coverage 0.665-0.694, lower bounds 0.634-0.663 against 0.633; 11 of 12,000 toys failed and count as not covering).
  `discrete_profile.py` runs rows in parallel (`--workers`, `--procedures`); seeds per row are unchanged, so the
  committed 300-toy study reproduces.
- **CI: Combine release gate fixed.** The conda-forge package is `cms-combine`, not `combine` (the first
  statistics-validation run could not solve); the job no longer pip-installs the lock over conda's NumPy. On GitHub it
  now passes: Combine 11.1.0 with ROOT 6.36.14, the datacard template within 2% of pyhf, 0 skipped.
- **CI: campaigns job.** The 300-toy discrete-profiling rerun runs its rows in parallel and compares per row with a
  cross-platform tolerance (coverage 2 points, mean mu-hat 0.01, bias 0.05, failures 2, identical verdicts); timeout
  180 min. First all-green statistics-validation run on GitHub: published, combine and campaigns pass.

## 0.6.11 (2026-10-12)

Hep-statistics audit (audit commit b5c3a55, findings F01–F04, checks T01–T30; evidence in VALIDATION.md,
STATS-AUDIT). Batch A (P0, T01–T08):

- **sci-fix: Poisson domain in the likelihoods (F01, T01).** `likelihood_limits.py` read a negative Poisson mean in an
  empty bin as an empty bin (a shape template interpolated below zero gave expected = -1 with a finite NLL). A
  negative or non-finite mean, or a zero mean with events, is now outside every likelihood (NLL = +inf); a zero mean
  with no events stays valid. `_lnl` and the profiled background `_b_hat` keep `s + b >= 0` (relevant for the
  two-POI fit, where a signal may be negative). No committed example number changed.
- **sci-fix: toy tails are bounds at zero exceedances (F02, T02, T03).** New `core/stats/tail_estimation.py`
  (Clopper-Pearson intervals and one-sided bounds, incomplete beta in pure Python, log-space Poisson tails). Every
  toy p-value of `likelihood_limits.py` and `statistical_toys.py` carries `toy_tail` {k, n, estimate,
  interval (68.27%), upper_bound or lower_bound (95%), convention}. **Behavior change:** `p_value_toys`,
  `toy_p_value_at_asymptotic_limit`, `toy_p_value` and their binomial errors are `null` where they used to report
  p = 0 or an error of 0 (k = 0; the error also at k = n). `statistical_toys.py ratio` counts toys it cannot evaluate
  (`toys_not_evaluated`) instead of reading them as non-exceedances.
- **sci-fix: fit verdicts (F03, T04, T05).** New `core/stats/fit_diagnostics.py`: the damped Newton search is
  unchanged, but every fit now returns `converged` or `failed` with reasons (finite NLL, positive-definite Hessian,
  EDM <= 1e-5; `max_iterations`, `line_search_stalled`, `hessian_not_positive_definite`, `invalid_domain`, ...). A
  best fit at `mu = 0` is checked by the KKT condition. A conditional NLL below the global one by more than 1e-4
  triggers a global refit and, if it remains, a failure (it was clipped to `q = 0` before). `shape-limit`,
  `shape-gof` and `contour` report `fit_diagnostics` and `status`; the CLI exits 1 (`failed`, a fit on the data) or
  3 (`incomplete`, only toy fits failed, or an open contour) instead of always 0. Failed toys are counted and make the
  result incomplete; toy p-values carry the range [k/N, (k+F)/N], while the toy CLs curves still include the q values of
  failed toys, which is why such a result is never ok. A better global minimum found by a refit restarts the limit or
  contour from it.
- **Contracts 2.2.0 (minor): statistical-result semantics (F04, T06–T08).** New optional fields: typed p-value bounds
  (`significance.local_p_bound`, `global_p_bound`), `global_n_toys`, `coverage.check` (`toys`, `exact-construction`,
  `analytic`, `not-checked`) with `n_toys`, `coverage`, `interval`, `cl`, `ensemble`, `failure_policy`, `failures`;
  `fit_diagnostics`; `likelihood.backend`, `model_ref`, `model_sha256`. New rules: a p-value or bound outside [0, 1],
  a confidence level outside (0, 1), a global p-value below the local one, expected bands that are not ordered
  `[low, high]` pairs, or `fit_diagnostics` failed under `fit_status: converged` are errors; untyped coverage, a
  global p-value without `trials_method` and toy coverage without its toy count are unresolved. The rules apply to
  artifacts of contract 2.2.0; older artifacts keep their outcome and get them with `validate.py --strict`. New
  capability `stats:result-semantics`, so a 2.1 reader refuses a 2.2 result that relies on them. New publication
  gate (`validate.py --gate publication`, `contracts.validate.publication_gate`): passed, unresolved or failed, with
  reasons (strict validity, fit status and diagnostics, typed coverage, global calibration of a scan, Bayesian R-hat
  and ESS, model and backend provenance, status labels). New converter `contracts/migrate_statistical_result.py`
  (refuses an artifact that breaks a 2.2.0 rule, names the rule; never invents coverage or a trials method).
- **hep-statistics: `scripts/result_artifact.py`.** Writes a `statistical-result` from a `core/stats` CLI output,
  keeping its status (a failed fit becomes `fit_status: failed` with the `failed` label) and writing a zero-exceedance
  toy p-value as a typed bound.
- **Examples.** The six example statistical-results state `coverage.check` (five `not-checked`: their toy studies are
  closure and pull checks, not interval coverage; `theory-comparison` `toys`; `published-comparison` `analytic`).
  Outputs regenerated for contracts 2.2.0 (only the version strings and `check` changed).

Batch B (P1, T09-T17, T22-T23):

- **Exact counting and asymptotic oracles (T09, T10).** Tests against SciPy roots, an independent Feldman-Cousins
  ordering and the closed forms of Cowan et al. (arXiv:1007.1727v3). New asymptotic calibration gate in
  `likelihood_limits.py` (`asymptotic_calibration`: the asymptotic p inside the toys' 99% exact interval, else
  inapplicable).
- **Toy CLs (T11).** `shape-limit --cls-toys` keeps the CLs+b and CLb exceedance counts per grid point, an exact-interval
  range for the limit (`observed_limit_mc_range`) and reports a limit decided by a floored denominator as unresolved.
- **Toy ensembles and coverage accounting (T12, T13).** New `core/stats/toy_ensemble.py`: explicit ensemble (no
  default), seeds from (seed, toy index), disjoint partitions, one outcome per toy, coverage C/N, (C+F)/N and C/(N-F)
  under a predeclared failure policy, a pass/fail/insufficient-precision coverage gate; no automatic retries.
- **Coverage grid (T14).** `examples/stats-benchmarks/coverage-grid/`: exact coverage of the classical, CLs and FC belts
  and 20,000-toy coverage of the asymptotic profile limit; a negative control (sigma_b ignored) is rejected.
- **SR/CR model card and backend equivalence (T15, T16).** `contracts/schemas/statistical_model.json` (nested as
  `likelihood.model_card`), `adapters/pyhf-combine/assets/model_card.py` and `backend_comparison.py`.
- **Published likelihood (T17).** `examples/stats-benchmarks/published-likelihood-sbottom/`: ATLAS-SUSY-2018-31 SRB from
  the HEPData pallet (checksum pinned) against preregistered paper values, with full CLs scans and bands.
- **Unfolding (T22, T23).** `unfolding_diagnostics.py outer-coverage`; `response-stat` accounts for every toy.

Batch C (P1, T18-T21, T24-T25): `skills/hep-statistics/scripts/covariance_fit.py`, `sweighted_fit.py`,
`bayes_calibration.py`; sci-fix of `bayes_diagnostics.py` (ties, constant chains, ESS and MCSE as Vehtari et al.);
`template_fit.py` refuses signed-weight templates; Bayesian contract rules (NUTS metadata, divergences, E-BFMI,
improper priors).

Batch D (P2, T26-T30, all EXPERIMENTAL): `eft_scan.py`, `discrete_profile.py`, `global_significance.py`,
`pcl_efficiency_ratio.py`, `ratio_estimation.py`. The discrete-profiling study (`examples/stats-benchmarks/discrete-profile/`) meets its
bias criterion; its coverage is not established at 300 toys per point (insufficient precision).

CI, documentation and evidence:

- **CI.** New required job `stats-backends` (`tests.yml`): the statistics tests with pyhf 0.7.6 and ArviZ 0.23.4, where
  a skip for a required backend fails (`tools/run_required_backends.py`). New workflow `statistics-validation.yml`
  (weekly, on demand, on release tags): full-budget campaigns, the published-likelihood reproduction (not-run fails)
  and a Combine 11.1.0 release gate. These workflows were written and their YAML checked here; they have not run on
  GitHub yet.
- **Wording.** CLs is described as a modified frequentist exclusion prescription (not "not a frequentist interval");
  a profile-versus-marginalized difference is no longer called a method systematic to add; frequentist constraint
  terms are `"constraint"` in `shape-limit` (`"prior"` kept as an alias; results carry `constraints` and the legacy
  `priors`); the Combine execution scope in `nuisance-modeling.md` matches VALIDATION; equation numbers of Cowan et al.
  are cited for arXiv v3 (one wrong number corrected).
- **Evidence.** `docs/evidence/statistics/` holds a source and claim ledger (checked by `core/evidence/ledger.py`) and
  a capability ledger with statuses supported, experimental or unvalidated, each with its tests and CI gate.

## 0.6.10 (2026-10-12)

- **batch-schedulers: `limits.max_gpu_hours`.** The Slurm poll reads `AllocTRES`; each attempt records
  `alloc_gpus` (`gres/gpu=N`, 0 for a CPU job, unknown while pending). GPU-hours are GPUs times elapsed time (or the
  walltime limit until the end is observed), allocated GPUs once polled and `resources.gpus` before that; usage
  reports `gpu_hours`. Work without GPUs counts 0 and is never refused by this limit. HTCondor counts requested
  GPUs.
- **batch-schedulers: `limits.alloc_cpu_factor`.** A site-declared allocated-per-requested CPU factor (>= 1) sizes
  `max_core_hours` before any allocation is observed: new jobs and attempts without `alloc_cpus` (queued Slurm
  tasks) count requested CPUs times the larger of this and the observed factor. Closes the first-submission
  under-count left open by the previous entry; usage reports `alloc_cpu_factor` (used) and
  `alloc_cpu_factor_observed`.
- **batch-schedulers: `max_core_hours` counts allocated CPUs.** The Slurm poll reads `AllocCPUS`; each attempt
  records `alloc_cpus`, core-hours use it when present (requested CPUs otherwise, as for HTCondor), and new
  submissions are projected at the largest allocated/requested factor seen in the campaign (`alloc_cpu_factor` in the
  usage). Fixes the 2× under-count on hyper-threaded GPU nodes found in GPU-CAMPAIGN-RUN once a pilot has been
  polled; the first submission and GPU-hours are covered by the two entries above.
- **batch-schedulers: first GPU campaign (documentation and evidence).** Two synthetic GPU chunks on NSTCCore V100
  through the adapter with `resources.gpus`, merged equal to a CPU recompute (GPU-CAMPAIGN-RUN). `batch-scheduling.md`
  now states that `max_core_hours` counts requested CPUs only (under-counting where a site allocates more, 2× on
  hyper-threaded GPU nodes) and that GPU-hours are not tracked (both lifted by the entries above), how
  `resources.gpus` renders and when to use `slurm.gres` instead, and to give GPU chunk results an additive device
  counter so the merge proves where chunks ran. NSTCCore site note, known limitations, capability matrix and
  `adapter.json` environment updated. No code change.

## 0.6.9 (2026-10-11)

- **docs/maintenance.md: real-hardware checks.** The three gated test modules (`HEP_TORCH_GPU_TEST`,
  `HEP_SLURM_TEST`, `HEP_HTCONDOR_TEST`), when to run them before a release, and how to report a GPU run on a pull
  request as a `gpu-tests` commit status (same-repository PRs by maintainers only; site tooling kept outside the
  plugin). First used on PR #41.
- **physics-ml: `check_pytorch_env.py` checks the build against each GPU.** It prints the build's compiled
  architectures and, per visible GPU, whether its compute capability is supported (NVIDIA's binary compatibility
  rules: same major and newer minor for cubins, exact for arch-specific cubins, any newer capability for PTX), and
  exits 3 when one is not. It also exits 3, printing torch's own reason, when `nvidia-smi` sees GPUs but the build
  cannot use them at all (observed: the CUDA 13.0 build on V100 nodes whose driver supports CUDA 12.9 at most, where
  it previously printed "CUDA available: False" and exited 0). Without CUDA it prints the compiled list via
  `torch._C._cuda_getArchFlags()`. Unit tests cover the measured builds; verified on a V100 with both builds and with
  the GPUs hidden.
- **physics-ml guidance:** `ml-analysis.md` treats device and precision as a source of category migration for
  scores that are cut on (evaluate where validated, or measure the migration as a systematic); `reproducibility.md`
  lists the GPU details to record and says to link a `computational-run` artifact from the `ml-artifact`'s `inputs`,
  since the `ml-artifact` has no environment fields.

## 0.6.8 (2026-10-11)

- **physics-ml: first GPU runs.** The assets ran on V100 and RTX PRO 6000 Blackwell GPUs through Slurm (torch 2.14.1,
  CUDA 12.6 and 13.0 builds): CUDA training with and without AMP agrees with CPU, inference, the transformer with fp16
  autocast and 2-GPU NCCL DDP pass; no GPU-only bug found. New opt-in GPU tests `tests/skills/physics_ml/test_gpu_real.py`
  (`HEP_TORCH_GPU_TEST=1`). `test_ddp_skeleton_two_gloo_processes` now hides the GPUs from its child processes: on a
  host with one visible GPU it failed ("invalid device ordinal"), and with two it silently tested NCCL instead of gloo.
  `deep-learning-guide.md` gains "GPU Builds, Clusters and DDP" (compiled architectures per build and how to read them
  without a GPU, emulated bf16, GPUs per DDP rank, AMP not always faster). Evidence in VALIDATION.md (TORCH-GPU-RUN).
- **VALIDATION known limitations:** the batch-adapter row is corrected (it still said fake schedulers only after the
  real Slurm and HTCondor campaigns).
- **hep-computing: checking what a Slurm cluster can give you.** `batch-scheduling.md` gains a read-only procedure
  for the picture the user chooses a partition from: capacity per partition without double-counting shared nodes,
  pending reasons, GPUs that are usable only with free cores beside them, access and QoS limits, what
  `--test-only` does and does not tell, fair-share standing, and one tiny confirming job. Sizing notes that sampled
  `MaxRSS` under-reports short pilots. Learned from a full resource check on NSTCCore (Slurm 24.05.1, 2026-10-10).
- **hep-computing: NSTCCore site note.** The QoS row is corrected (the partition QoS imposes its limits; the job's
  own QoS stays `normal`, it is not replaced); new rows for the RTX PRO 6000 Blackwell node (`b6000-al9_devel`,
  checked with a CUDA kernel) and for partition access and QoS limits. Snapshot values (queue counts, idle
  resources, one user's fair-share figures) are removed from the note: they change by the hour; the note keeps
  configuration and behaviour.

## 0.6.7 (2026-10-10)

- **hep-computing: NSTCCore Slurm site note.** New reference
  `skills/hep-computing/references/batch-site-nstccore-slurm.md`: what Slurm 24.05.1 did on the NSTCCore (TWGrid)
  cluster on 2026-10-10, each fact with its site-guide or SchedMD 24.05.1 page or the observation (partition tiers
  that starve the default partition, memory requests that add billed CPUs, over-memory jobs that swap instead of
  failing, `--export=NONE` rebuilding the login environment, `DerivedExitCode`, sampled `MaxRSS`, Fair Tree priority),
  and how to configure the adapter there. `batch-scheduling.md` links it, and its Slurm tool-facts rows confirmed by
  the first real Slurm campaign (synthetic, 10 chunks, merged equal to a local recompute) now say "observed".
  Follow-up rows: `--export=NIL` starts bare (no `HOME`, no `module`), `srun --container` is silently ignored (no
  `oci.conf`), PyROOT needs `PYTHONPATH=$ROOTSYS/lib` with the `libxxhash` workaround.
- **batch-schedulers: Slurm demonstrated on synthetic data.** `RealSlurmTests` is now a real gated test
  (`HEP_SLURM_TEST=1` plus `HEP_SLURM_CONFIG` naming a reviewed configuration: two synthetic chunks submitted,
  polled, merged and reported) instead of a placeholder skip; it passed on Slurm 24.05.1. `adapter.json` lists Slurm
  `demonstrated-on-synthetic-data` with `tested_versions ["24.05.1"]`, which raises the adapter to
  `demonstrated-on-synthetic-data`. Evidence in VALIDATION.md (NSTCCORE-SLURM-RUN).
- **CI: each pull-request commit runs the workflows once.** `tests` ran on both `push` and `pull_request`, so every
  commit of a PR branch ran the whole suite twice; it now runs on pushes to `main`, on pull requests, weekly and on
  demand. `guard` (path allowlist, secret scan) is unchanged: it still runs on every push and every pull request,
  including pull requests from forks. No plugin change.

## 0.6.6 (2026-10-10)

- **README: package size statement updated** to about 1,070 files and 8.6 MB (the release manifests add about
  0.2 MB each; `check_packaging` flags a statement more than 10 % off).
- **hep-computing: EOS rows of the CERN HTCondor site note observed (work order T06, E2f).** One espresso job
  read a synthetic file from EOS with `xrdcp` and returned outputs through `output_destination`: credentials and the
  EOS mount are present in the job, checksums match, and `output`/`error` are sent to the destination as well (only
  the user log stays on AFS). Documentation only.

## 0.6.5 (2026-10-10)

- **hep-computing: CERN EOS storage note (work order T06).** New reference
  `skills/hep-computing/references/storage-cern-eos.md`: what EOS is, how to address an instance, copying with
  checksums, the mounted file system versus `root://`, versions, recycle bin, quota, ACLs, tokens, and remote
  reading from ROOT and uproot. Every row cites the EOS project site or the EOS 5 documentation (read 2026-10-10) or an
  observation on lxplus with synthetic files. Observations the documentation does not state: overwriting a file
  through the mount keeps no version (an `xrdcp -f` overwrite does); a normal user cannot purge the recycle bin;
  `eos whoami` through the `eosuser` redirector shows nobody; an interrupted upload leaves nothing under the target
  name. Linked from `SKILL.md` (Resources trimmed to stay within the 8,192 B budget), from the HTCondor site note's
  EOS row, and from a new "Remote files (XRootD)" section in `python-hep-coding-patterns.md`. Reference inventory
  regenerated. No code change.

- **CI: the `lint` job passes again.** ruff 0.16 (UP017) asks for the Python 3.11 UTC alias in
  `core/partition/runner.py`; the runner keeps `datetime.timezone.utc` because it runs under the batch workers'
  Python 3.9 (work order T03), now with `# noqa: UP017` and a comment. No runtime change.

- **Tests: the batch-partition example's committed output is compared up to float rounding.** `sum_cos` is a numpy
  reduction whose last digits differ between hosts and numpy builds (lxplus with numpy 1.23.5 against the committed
  file: `…253` vs `…256`), which failed the byte comparison; counts, states, digests and labels stay exact, floats are
  compared at a relative 1e-9, and the helper has its own test. No runtime change.

## 0.6.4 (2026-10-10)

- **batch-schedulers: three follow-ups from the first real HTCondor runs (work order T03).** `watch` stops as soon
  as nothing is queued or running (`nothing-active` when planned chunks were never submitted; before, a pilot watch
  polled to `max_polls` and held the campaign lock); the HTCondor backend reads the event log once more when the
  queue no longer lists a job before falling back to `condor_history` (on AFS the log trailed the queue by seconds
  and the history record came minutes later); a changed configuration with the same files freezes as its own
  request file under the same digest and `submit --bundle` chooses by the configuration hash (before,
  `bundle.request_differs` left no way forward but a new campaign directory). `core.partition.bundle.config_hash`
  is the one formula both sides use. Shim: a `lagged` event-log mode. Tests: watch, HTCondor backend, bundle.

## 0.6.3 (2026-10-10)

- **batch-schedulers: first real HTCondor runs (CERN local pool from lxplus, HTCondor 24.12.16, work order T03).**
  The HTCondor backend takes `htcondor.site_attributes` (a map of ClassAd attribute to string, integer or boolean,
  written as `+Name = value`: CERN's `JobFlavour`, `MaxRuntime`, `WantOS`), accepts `resources.time_limit` (which
  sizes `limits.max_core_hours` and must agree with a `MaxRuntime` attribute), and `htcondor.schedd` (a host name, or
  `caller` for the shell's `_condor_SCHEDD_HOST`): the schedd is recorded with each submission and passed as `-name`
  to every later `condor_q`, `condor_history` and `condor_rm`, so a campaign stays on its schedd when the site's
  mapping changes. Two `condor_submit` failure texts observed on the pool (credential step, rejected transaction)
  settle the attempts as `not-submitted` instead of leaving the submission unconfirmed; `condor_history` is called
  with `-match N`; the cluster-level events `035`/`036` (proc −1, HTCondor 24.12) no longer make the event log
  unparsable. `core/partition/runner.py` no longer uses `datetime.UTC` (3.11+): on workers with Python 3.9 every job
  died before the worker started. `RealHTCondorTests` runs a two-chunk synthetic campaign with `HEP_HTCONDOR_TEST=1`
  and `HEP_HTCONDOR_CONFIG`; it passed on lxplus, and two synthetic 5-chunk campaigns (shared-filesystem and transfer
  modes) merged equal to a local single run. `adapter.json`: HTCondor `demonstrated-on-synthetic-data`,
  `tested_versions ["24.12.16"]`. New reference `hep-computing/references/batch-site-cern-htcondor.md` (CERN batch
  documentation facts with dates, what 24.12.16 did, and how to configure the adapter there); tool-facts rows of
  `batch-scheduling.md` updated to "observed". Evidence: VALIDATION.md, CERN-HTCONDOR-RUN.

## 0.6.2 (2026-10-09)

- **research-communication: identifiers missing from a ledger.** An arXiv number, DOI or INSPIRE record that a ledger
  row lacks is looked up at a primary source the session may reach (INSPIRE-HEP, arXiv, doi.org) and reported as
  looked up there with source and date, not as a ledger claim, and never supplied from memory (`SKILL.md` invariant;
  AMS `source-policy.md` rule with matching against title, journal reference and date). Before, the skill correctly
  refused to quote from memory but did not try an allowed source. Live check in a sandboxed configuration: the B/C
  paper (PRL 117, 231102) was looked up at INSPIRE (record found, no arXiv e-print attached) and arXiv, and reported so.

## 0.6.1 (2026-10-09)

- **Validation hint for profile vocabulary.** `contracts/validate.py` (through `contracts/schema.py`): an unknown
  vocabulary term with a profile prefix (for example `crflux:top-of-instrument`) now says that the prefix comes from a
  profile's vocabulary and that the artifact must be validated with `--profiles-from <project config>`. Before, the
  plugin's own AMS example artifacts failed without a hint. New test: all shipped AMS example artifacts validate with
  the profile bound.
- **Guidance from a synthetic-twin study** (B/C ratio, run in a sandboxed configuration):
  hep-statistics `inference-recipes.md` gives a measured case where `-2 log lambda <= 1` covered 0.57-0.79 instead of
  0.683 at low counts and a toy-calibrated Neyman construction restored it, and asks for yield-scaled backgrounds
  inside the likelihood; hep-analysis `systematics.md` adds how to test whether a variation's shift is significant
  (Barlow's subset approximation for data plus a paired bootstrap for the simulation); the AMS ratio blueprint
  (`charged-cosmic-rays.md`) states that cross-species fragmentation backgrounds scale with the other yield and are
  solved jointly; hep-computing `host-notes.md` warns against hard-coding the plugin cache path in project scripts.
  Reference inventory regenerated.

## 0.6.0 (2026-10-09)

- **Tool contracts (AGENTIC-R5 T4.7, F14, F16).** New sidecar schema `contracts/schemas/tool_contract.json`
  (`contract_version` 1.0.0) and `contracts/tool_contract.py`: per operation, every command-line option mapped to one
  input, inputs and outputs with quantity kind and unit (caller-bound unit symbols such as `{X}` must come from an
  input), failure states by exit code (one meaning per code), required capabilities (only ones this reader implements),
  purposes (exploration, fixed execution, validation; never formal analysis), operators from an operator-semantics table,
  and side effects (no network). The checker runs `--help` and compares the usage line with the declared options in both
  directions, required ones included; `--scope` checks that every operation of an enabled scope has a passing contract
  that declares the scope's purpose. First contract: `contracts/tool_contracts/cosmic_ray_flux.json`; tests also run the
  tool and check the declared outputs and failure exits. `cosmic_ray_flux.py` now refuses a confidence level outside
  (0, 1), and an exposure times bin width or a flux that under- or overflows (exit 2); before, it accepted the levels
  and crashed or printed `Infinity` on the others. A contract authorizes nothing. Tests in
  `tests/contracts/test_tool_contract.py`.
- **Operator semantics for bounded recipes (AGENTIC-R5 T4.6, F04, P05).** New sidecar schemas
  `contracts/schemas/operator_semantics.json` and `recipe.json`, the table `contracts/semantics/tables/differential_flux.json`
  (counts to differential flux: background subtraction, unfolding with or without efficiency in the response,
  efficiency correction, plain or effective exposure, bin width) and the recipe
  `contracts/semantics/recipes/flux_from_counts.json`, bound to the table by canonical SHA-256. `contracts/recipe_semantics.py`
  checks that quantity kinds (and so units) chain from input to estimand, that each step's required effects are already
  applied and its forbidden ones not, that no effect is applied twice, counting effects recorded by upstream artifacts
  (`--upstream`: `included_corrections`, `corrections[].effect_id`; a name outside the table fails closed), that the
  result carries the effects the estimand requires, and that every other effect of the table is applied or listed in
  `not_applied` with a reason (the shipped recipe declares that it does not unfold), and that a step's named tool has a
  passing contract listing its operator. Effects the recipe claims as already applied upstream must be recorded by an
  `--upstream` artifact (without one they are reported as unverified), and an upstream artifact with no such record
  fails. A changed table no longer matches the recipe. A general Recipe IR is not part of this. Tests in
  `tests/contracts/test_recipe_semantics.py`.
- **Attestations with separate axes (AGENTIC-R5 T4.5, F11).** New sidecar schema `contracts/schemas/attestation.json`
  (`attestation_version` 1.0.0) and `contracts/attestation.py`. The subject is a frozen bundle digest and a scope
  (observable, data, recipe digest, calibrations, assumptions, purposes). Three axes are reported separately and never
  combined: capability (`supported`/`unsupported` by this reader), review (each review binds the bundle digest, the
  scope digest and its evidence files' SHA-256, re-hashed under `--evidence-root` without following links; states
  `absent`, `unbound`, `rejected`, `bindings-unchecked` without `--bundle` and `--recipe`, `evidence-unverified`,
  `roles-unchecked`, `roles-incomplete`, `out-of-scope` for a `--use` beyond the reviewed scope, `accepted-as-recorded`:
  the reviewer's identity and the protected record are not verified here) and lifecycle (revocation and expiry from a fresh status source; states
  `unknown`, `draft`, `withdrawn`, `superseded`, `not-yet-effective`, `expired`, `revoked`, `active`). `--bundle` and
  `--recipe` must match the subject; a mismatched or malformed attestation gets no axis states at all, and a status
  age above one day is refused. The exit code says only whether the attestation was evaluated; whether a use may
  proceed is the trusted gate's decision (T4.1). Tests in `tests/contracts/test_attestation.py`.
- **Data release manifest schema and checker (AGENTIC-R5 T1.2, plan basis §7.3).** New sidecar schema
  `contracts/schemas/release_manifest.json` (`manifest_version` 1.0.0, within the schema engine's keyword set) and
  `contracts/release_manifest.py`, meant to run on the custodian side from protected copies. A pass needs every input
  (fail closed): the release directory holds exactly the listed regular files with their sizes and SHA-256 (links and
  unlisted files refused); the approval record names `approval_ref`, binds the manifest digest (without
  `approval_ref`), its purposes, destinations digest and validity period, and is valid now (authority `data-release`,
  held by the approver in the required approver list); the release ledger shows no reuse of `release_id` for other
  content; revocation status comes from `status_source`, is fresher than `max_status_age_s` and does not list the
  release; every effective destination (service, tenant, region, model family, exact model when named, tools, network,
  recipients, logging) is allowed, and an absent tool, network or recipient list is a failure, as is a directory the
  check cannot list or a malformed approver list, ledger entry or revocation entry. Formal analysis is not a release
  purpose. The checker verifies bindings, not the trust anchor (Q-06); passing releases nothing (T1.8). Tests in
  `tests/contracts/test_release_manifest.py`.
- **Execution-bundle freezing (AGENTIC-R5 T4.2 freezing tool, F06, X05, X14).** New `core/partition/bundle.py` and
  `batch_campaign.py freeze` / `verify-bundle`: a write-once `bundles/<digest>.json` lists, with full SHA-256, size
  and mode, the campaign files, the worker tree, the interpreter (resolved through links and re-checked), an
  environment lock and the container image, which must be pinned by digest (a sourceless `.pyc` counts as code); the
  digest also binds the campaign uid, manifest hash and the data exposure recorded at freezing. The command follows a
  closed grammar: an absolute interpreter, an absolute bundled worker script, then only flags, `--name=value`, single
  placeholders, numbers, plain ASCII words and absolute paths to bundled worker files without braces, each re-resolved
  by `verify` (a repointed link is a change); the template is checked again at freezing, a worker's `#!` line must be
  one absolute interpreter without arguments (read as the kernel reads it) and is hashed; launchers (`env`, `nice`,
  `nohup`, ...; judged by the resolved name) and `#!` scripts are refused as interpreters; the worker root may not
  contain the campaign. A bundle frozen for another campaign (directory, uid, manifest) is refused. The file carries
  an approval request (bundle digest, config hash, limits, scope) and approves nothing. `submit`/`resubmit --bundle`
  re-hash it and refuse a changed campaign (`bundle.changed`); the submission records the digest and the artifact
  lists it. Verification of approved bytes at execution stays with the trusted submitter (T3.5). Tests in
  `tests/core/test_partition_bundle.py`, `tests/adapters/test_batch_bundle.py`.
- **Marketplace lists hep-research only.** Both catalogs (`.claude-plugin/marketplace.json`,
  `.agents/plugins/marketplace.json`) no longer list `ams02-research`; the READMEs say so and how an installed copy is
  handled. hep-research never depended on it; companion profile support is unchanged.
- **Campaign limits, attempt identity and confirmed cancellation (AGENTIC-R5 T3.4, X08, X09).** New
  `core/partition/limits.py`: an optional `limits` configuration section (`max_submissions`, `max_total_jobs`,
  `max_concurrent_jobs`, `max_core_hours`, `max_resets_per_chunk`; values are the site's, none are defaulted) stops a
  submission or reset that would exceed it before anything is written (`limits.exceeded`); unknown and abandoned
  attempts count as used, and as running (an unknown one until a poll sees it end) until `clear_orphan_risk` (CLI
  `clear-orphans`) records that every job the scheduler lists under the submission's tag has ended; without a walltime
  core-hours are unbounded, so `max_core_hours` refuses. `states.decide` caps resets (`resets-exhausted`), so a reset
  no longer bypasses the limits. Attempts record `global_attempt_id` (`<campaign_uid>:<attempt_id>`). `cancel` records
  each command's exit per job (`requested`, `request-failed`, `request-unconfirmed`), also targets jobs found under
  the tag of unconfirmed or abandoned submissions, and an attempt is `termination_observed` only when a later poll
  sees a final state. Unknown, abandoned and orphan jobs leave append-only `resource_risk` records, carried into the
  campaign artifact with the usage. `batch_config.validate` checks the section. Tests in
  `tests/core/test_partition_limits.py`. Limit values and a real pilot remain open (Q-07, T3.3).
- **Structured data exposure in change review (AGENTIC-R5 T4.4, K06).** `review_analysis_change.py` reports a
  `data_exposure` (`state`, `basis`, as in the 2.1.0 envelope) per change and accepts a structured record. A missing
  `looked_at` (basis `none`), an empty list, a string, or an entry it does not recognize as control-region, sideband,
  simulation, calibration or validation data in a closed grammar (one kind of data per entry; simulation entries never
  name data) is `unknown`, never unexposed; such a change gets the new decision `exposure-unknown` instead of
  `accept`. A malformed structured record is an input error (exit 2). Legacy text can only raise a structured state.
  Tests in `tests/skills/hep_analysis/test_review_analysis_change.py`.
- **Independent of companion plugins.** hep-research installs, updates and runs without `ams02-research`; a companion
  owns its compatibility check (its preflight) and declares no host dependency on hep-research.
  - `tools/check_host_manifests.py` parses `dependencies` (bare name, `name@marketplace`, object) in both plugin
    manifests and both repository catalogs and fails on an edge between hep-research and another listed plugin, in
    either direction; unrelated dependencies are left alone. No such edge exists today; the test
    (`tests/tools/test_companion_independence.py`) is protective.
  - Context stanza: a companion's profile, including a `local_profile_paths` entry known to be the companion's folder,
    is used only through its `<plugin>:profile` skill after that skill's preflight; nothing scans for companions; a
    failed preflight makes that profile unavailable and other work goes on. `docs/profile-authoring.md` replaces the
    advice to declare `"dependencies": [{"name": "hep-research", "version": "^0.3"}]` with the preflight, and states
    that package compatibility and profile validation are separate.
  - `contracts/registry.py` and `contracts/project.py`: `--local` or `--registry` without a value is a usage error
    (exit 2, JSON `error`) instead of a traceback with exit 1, which a caller would read as a validation failure, or a
    silently ignored flag; the same local folder given twice (for example in `local_profile_paths` and through
    `--local`, or twice in the config) is one profile instead of a `registry.duplicate_id` error. Folders with the same
    profile ID still fail. `tests/contracts/test_companion_validation_cli.py` covers the CLI cases a companion checker
    relies on.
  - The marketplace catalogs pin `ams02-research` 1.2.1 (commit `32d538a`, was 1.0.1 at `1c3f590`): the companion
    release without a host dependency on hep-research; its own check accepts hep-research `>=0.4.0,<0.6.0`. An
    installed 1.1.0 or earlier still holds hep-research at 0.4.x until the companion is updated first (README).

## 0.5.0 (2026-10-08)

- **Agent-run checks are advisory, blinding tools fail closed (AGENTIC-R5 WP0′).** Built from the R5.4 agentic planning
  basis; no host configuration is qualified by these changes, and the interim rules still hold: public or synthetic
  data only, and no real sealed values in an agent session.
  - The verified R5 patch is applied: a newer contract major version is rejected (`contract.unsupported_major`);
    `dependencies.py --revocations` marks revoked artifacts without changing their bytes; `contracts/verify_run.py`
    recomputes a run's input and output hashes; float32 caches, Latin-1-decodable binary and `hist(histtype='step')`
    are caught; a bad runner template writes meta and exits 2. Follow-ups: numeric dumps that decode as UTF-16 are
    unscanned instead of passing, and float copies match exactly (no float16 false positives).
  - `dependencies.py` reports `dependency_consistency_ok`; `formal_use_allowed` is always `false` (formal use is decided
    only by a trusted gate). The analysis contract's `unblinding_authorization` is now `unblinding_record_ref`, never
    filled by the agent.
  - `audit_blinded_outputs.py scan` prints a fixed status only (no sealed value, token, file, line or count); details go
    to `--report`. The tolerance comes from the sealed file; `seal` prints no count and seals more derived quantities
    (difference of sums, square roots, fractions, (N-B)/sqrt(B)). Signs, the Unicode minus and percentages are matched;
    unreadable arrays and symlinked directories are incomplete; invalid bin edges stop `seal` and `mask_blinded_bins`;
    `check_figure` reads every figure text, contour fills and sealed y values, and `check_figure_report` lists what it
    cannot check.
  - Campaigns and local runs refuse invalid command templates and manifests before writing (only `{start}` `{stop}`
    `{seed}` `{out}` `{id}`; safe chunk IDs, so `../` cannot escape the campaign).
  - Instruction texts: unblinding is done by a person outside the agent session; real data arrive as released blinded
    derivatives; sealing and scanning with real values belong to the data custodian; batch submission is unsandboxed
    execution, limited to synthetic test environments; private local and companion profiles are read only when the
    project's `agent_policy` allows them on a qualified host (none is yet); "tested" hosts are not qualified for private
    data. `tools/check_instruction_text.py` (run by `run_all_checks.py`) guards these texts.
  - Code release identity: `tools/release_manifest.py` writes the manifest of a release bundle (git-listed files,
    full SHA-256, size and mode, sorted, no symlinks) and its digest, verifies a tree against it, and, in CI
    (`release-manifests` job), checks that every recorded `release-manifests/<version>.json` matches its published tag
    and that recorded manifests are only ever added.
  - **Contracts 2.1.0 (minor).** New optional envelope fields: `versions.plugin_release` (`{release, digest}` from
    `contracts/identity.py`: the full digest when the installed tree matches its own recorded release manifest,
    otherwise `unreleased`/`unknown`), `required_capabilities` (a reader rejects one it does not implement) and a
    structured `data_exposure` (`state`, `basis`). `inputs[].version` must be a version. The validator now warns on a
    newer minor contract (an error with `--protected`), checks `versions.contracts` against `contract_version`, and
    warns on unknown top-level keys; `dependencies.py` validates every source as a contract artifact. The batch
    computational-run records the runner hash and resource-request hash in full (older 16-digit hashes still match),
    plus the full manifest hash. Example outputs are regenerated for 2.1.0.
  - **Project config schema 1.1.0.** `agent_policy` (policy version, allowed model-context classes, protected paths
    without `..`, data release manifests checked by SHA-256, unblinding outside the agent session, authoritative copy);
    `contracts/project.py` checks `schema_version` (a newer minor or another major is refused), closes the `blinding`
    block from 1.1.0, adds `blinding.regions`, and requires the block when `agent_policy` is present.
    `contracts.project.load_blinding` reads it validated; `core.blinding.load_project_blinding` refuses a policy without
    a blinding block instead of reporting nothing blinded.
  - **Batch execution hardening (WP3′).** Every scheduler call has a timeout (`scheduler_timeout_s`, default 120 s) and
    an allow-listed environment (`env_passthrough` adds names; credential-like names are refused); Slurm jobs use
    `--export=NONE`, HTCondor jobs `getenv = false`. Only a client that could not start records `not-submitted`; a
    timeout, exit 0 without a job ID or a failure after the call keeps the submission unconfirmed. Each submission has a
    tag (`hepr-<campaign uid>-<submission>`, the job name / `batch_name` and `HepResearchTag`); new `reconcile` lists
    the scheduler's jobs under it, and `confirm` refuses job IDs not in that list. `abandon` records `abandoned`.
    `cancel` records each command's exit and reports requests, not terminations. Configuration strings are single-line
    with strict names; `worker_python` and `transfer_input_files` are absolute. Collection never follows symbolic links
    and caps output size; `merge` refuses chunk files `collect` did not record and warns about collected orphan outputs.
    `submit --plan-digest` binds a submission to its reviewed dry run. The runner (`worker_timeout_s`), the local
    executor and `local_partition.py run` (`--timeout`, `--env-passthrough`) apply the same timeout and environment
    rules.

- **Choosing a SymPy interpreter (SYMPY).** `skills/hep-computing/scripts/find_python.py` finds a Python >= 3.11 that
  imports the packages a task needs (default SymPy). It tries, in order, `--python`, `HEP_RESEARCH_PYTHON`, the
  calling interpreter and `python3` on PATH, and scans nothing else. It reports the chosen path with its Python and
  package versions, or a `failed` status with every candidate's reason. hep-theory runs it before SymPy work and
  records the interpreter and versions in a `computational-run`.
- **Missing SymPy explained.** The theory-profile `derive.py` scripts and `examples/qed-prediction/run.py` print a JSON
  `failed` status naming the missing package and exit 2, instead of a traceback; `--help` works without them.
  Theory-profile tests skip, rather than error, when SymPy, NumPy or SciPy is missing.

## 0.4.0 (2026-10-08)

- **Live routing harness and new routing cases (T19).** `evals/routing/run_routing_eval.py` (repository level, outside
  the plugin) runs the routing cases through headless `claude -p` (Codex commands are built and parsed, not yet run),
  one pass per case, in a fresh folder with read-only tools, a pinned model, per-case and total budgets and a check
  that no other plugin loaded; it records the skills loaded and profile files read, scores strict and lenient routing,
  and compares with a committed baseline per CLI, CLI version and model. Scored summaries are committed; raw transcripts
  are not. The case set grows from 118 to 150: Simplified Chinese, Japanese and German cases, adversarial cases (a tool
  is named but the deliverable belongs to another skill), quick questions and two-turn handoffs, all covered by the
  static check.
- **Saturated-model goodness of fit (T22).** `likelihood_limits.py shape-gof` tests a shape-limit model (with its
  nuisances, constraint terms and `mc_stat`) against the saturated model, with μ fitted or fixed, and calibrates the
  statistic with toys from the fitted model; the χ² reference is reported and labeled approximate. Toy p-values are
  uniform under the null at low counts, where the χ² reference is not.
- **Asymmetric uncertainties (T22).** `skills/hep-statistics/scripts/combine_asymmetric.py` combines measurements with
  asymmetric errors by Barlow's linear-variance or linear-σ likelihoods, and adds several asymmetric uncertainty
  sources on one result by matching cumulants (quadratic or piecewise model, with the central value moved so the mean
  is kept). Closure against the exact pooled likelihood of lifetime measurements and against a Monte Carlo sum.
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
