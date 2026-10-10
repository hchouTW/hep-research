# Changelog — hep-research

Release notes for the plugin. Each entry says what changed in behavior; evidence is in [VALIDATION.md](VALIDATION.md).
Software checks establish contract consistency only, not physical validity.

## Unreleased

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
