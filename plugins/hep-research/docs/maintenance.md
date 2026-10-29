# Maintenance

Run everything from the plugin root. The aggregate check is the gate for any change:

```bash
python3 tools/run_all_checks.py --out <dir>      # layering, stanzas, registry, ledger, AMS-optional, routing (static),
                                                 # packaging, budgets, host validator, unit and profile tests
python3 tools/check_relocation.py --out <dir>    # the same from a copy at a path with spaces and another cwd
```

For a subset of the unit tests name the modules (`python3 -m unittest tests.tools.test_check_packaging_size`) or
use `python3 -m unittest discover -s tests/tools -t .`; naming only the package (`python3 -m unittest tests.tools`)
runs 0 tests, because the test packages have empty `__init__.py` files.

Tests come in two tiers. The fast tier is the default. `HEP_SLOW_TESTS=1` adds the slow tier (for example the full
Feldman-Cousins tables, the 10,000-mutation contract fuzz and the full theory-comparison example). `run_all_checks.py`
runs each test module in its own process with a time limit (`--module-timeout`, default 600 s, or the
`HEP_MODULE_TIMEOUT` environment variable) and records every module's duration. The slow tier needs more:
`tests.examples.test_stats_benchmarks` alone takes about 525-545 s there and timed out under parallel load, so the
weekly `latest` CI job, which runs the slow tier, sets `HEP_MODULE_TIMEOUT=1800`; do the same for a local slow-tier
run (`HEP_SLOW_TESTS=1 HEP_MODULE_TIMEOUT=1800 python3 tools/run_all_checks.py`) rather than reducing toys, seeds or
tolerances. A fast-tier module listed under `slow_modules` (over 60 s) belongs in the slow tier. Modules start
slowest first, using the durations recorded in `tools/module_timings.json`. CI splits the run into parallel jobs:
`--part units --shard K/N` runs one of N shards of the test modules, balanced by those durations, `--part static`
runs the profile suites and the static and host checks, and `--part ams-optional` runs `tools/check_ams_optional.py`
(the generic suites again in a copy without the AMS-02 profile; the slowest check, so it has its own job).
`--part checks` is `static` plus `ams-optional`. Refresh the durations from the CI check-runs (the median per module
over the units shards of one run on main) when the balance drifts; a module with no record gets the median and still
runs. Every check records its seconds; failed test ids with their traceback tails are printed and, with
`--summary FILE` (CI: `$GITHUB_STEP_SUMMARY`), written as Markdown. Each units run records its plan (the full module
list, its SHA-256 and the shard's modules), and the `checks-complete` job runs `tools/reconcile_check_runs.py` over
every checks record of the run: each expected run present once, of the tested commit, passing, with only the host CLI
checks skipped, every planned check reported, and the shards partitioning the module list of this tree. A missing
record fails the gate; equal test counts are never taken as evidence. Every subprocess call in the tests and tools
has a timeout (`tests/tools/test_subprocess_timeouts.py`).

**Selective CI on pull requests.** A `plan` job runs `tools/ci_plan.py` first.
- **How the plan is made.** The pull request's changed files (its merge commit against `HEAD^1`) go through the impact
  map in `contracts/rules/registry.json` (`impact` groups; `contracts/rule_registry.py impact`). The plan is the test
  modules and parts (`static`, `ams-optional`) those groups name, plus any changed test module, plus every test module
  that imports a changed test helper (a non-test `.py` under `tests/`; a helper nothing imports by name is the full
  run).
- **When it is the full run.** Any change the map cannot bound runs everything:
  - a file outside `plugins/hep-research/` (workflows, root `evals/`);
  - CI tooling (the runner, the reconciler, `ci_plan.py`, `check_ams_optional.py`, module timings, the lock,
    `pyproject.toml`);
  - a path no impact group covers, or a group marked `full`;
  - an unreadable diff.

  Pushes to main, the weekly and manual runs are always full, so a gap in the map is caught on main within the day.
- **What each job does with it.** Each checks job runs `run_all_checks.py --plan`:
  - the units shards split only the selected modules;
  - the AMS-optionality job runs only the selected modules that are in its suites (`ams_optional_modules` in the
    plan; the part is selected when there is at least one), plus its few-second fixed steps (registry without the
    AMS-02 profile, Paths B and C, two profile suites); when an impact group names `part:ams-optional` (profile
    changes) or the plan is full, it runs all of its suites;
  - a part the plan does not select skips installing the pinned set and writes a record that says so (`selection`).
- **What the gate checks.** `checks-complete` recomputes the plan itself and passes it to
  `reconcile_check_runs.py --plan`. Every record must name that plan's digest, the shards must cover exactly the
  selected modules, the AMS-optionality run must have run exactly its planned modules, and every part, selected or
  not, must have its record.
- **Making selection work for more changes.** Extend the impact groups. A path they do not cover keeps the full run,
  which is the safe default.

`check_ams_optional.py` has its own limit (`AMS_OPTIONAL_TIMEOUT`, 1200 s). It takes about 190 s locally and 7–10 min
on CI runners, which had reached the 600 s module limit.

Software checks show contract consistency only, not physical validity. Report pass, fail, skip and unverified
separately; a skipped test (missing tool) is unverified, never passing.

## Real-hardware checks

CI has no GPU and no batch scheduler, so three test modules are gated and run only where a maintainer turns them on,
on hardware the maintainer may use:

| Variable | Test | Needs |
|---|---|---|
| `HEP_TORCH_GPU_TEST=1` | `tests/skills/hep_ml/test_gpu_real.py` | a CUDA GPU; two visible GPUs for the NCCL test |
| `HEP_SLURM_TEST=1` + `HEP_SLURM_CONFIG` | `RealSlurmTests` in `tests/adapters/test_batch_slurm.py` | `sbatch`, a reviewed batch configuration |
| `HEP_HTCONDOR_TEST=1` + `HEP_HTCONDOR_CONFIG` | `RealHTCondorTests` in `tests/adapters/test_batch_htcondor.py` | `condor_submit`, a reviewed batch configuration |

Setting a variable is the approval to use that hardware or account. Without it the tests skip, and a skip is
unverified, never passing.

- **Before a release that changes `hep-ml` GPU paths** (assets, `scripts/check_pytorch_env.py`,
  `test_gpu_real.py`): run `check_pytorch_env.py` and the hep-ml test modules with `HEP_TORCH_GPU_TEST=1` on
  every GPU type claimed in the capability matrix (each with a torch build compiled for it; the script exits 3 when
  the build cannot use the GPU), one job with two GPUs. Before a release that changes the batch adapter, run the
  matching scheduler test. Record the result in `VALIDATION.md`; a type not rerun stays at its last recorded date.
- **On a pull request**, report the GPU run as a commit status with context `gpu-tests` on the PR's head commit
  (`gh api repos/<owner>/<repo>/statuses/<sha> -f state=... -f context=gpu-tests -f description=...`), with a
  comment giving the GPUs, torch builds and test counts; a new commit needs a new run. Run it only for
  same-repository pull requests by maintainers: code from a fork never runs on a maintainer's cluster account.
  Keep the tooling that submits the jobs outside the plugin, since it holds site facts (partitions, environments).

## SKILL.md size budget

`tools/measure_entrypoints.py` (run by `run_all_checks.py`) sets the budget (upgrade plan B-01, 2026-10-17): a
`SKILL.md` above 12,288 bytes gives a warning, which an entry `"<skill>:bytes": "<reason>"` in
`tools/budget_exceptions.json` may waive; above 16,384 bytes or 500 lines it fails, with no exception.
`tests/skills/test_routing_tables.py` applies the same 12,288-byte limit as a failure (it reads `BUDGET`; a waived
skill is held to 16,384) and keeps each Resources table at 1.5-3 KB (B-02); decisions D2 and D1, 2026-10-23, which
replaced the separate 11,264-byte and 2.5 KB test limits. SKILL.md plus its entry reference stays within 25,600 bytes
(B-03), the budget that binds. A description
stays at or under 1,024 characters, the limit of the [Agent Skills specification](https://agentskills.io/specification),
and the profile registry at or under 3,072 bytes (`REGISTRY_BUDGET` in `contracts/registry.py`). Until 2026-10-17
the budget was 8,192 bytes per `SKILL.md`. On 2026-10-13 the three files that sat at the limit were trimmed by moving their reference and script lists into index
sections of their primary reference (`hep-detector`: section 11 of the principles summary; `hep-statistics`:
"Skill scripts" in the core/stats guide; `hep-computing`: "Scripts" in the engineering playbook); they now measure
6,566, 7,545 and 7,598 bytes. On 2026-10-17 (upgrade batch 0b) the communication skill measured 9,322 bytes before it
was split; on 2026-10-19 (the split) hep-computing measured 9,366 and hep-authoring 8,347 bytes. Measured on
2026-10-29 (hep-review added, `wc -c`): hep-computing 9,912, hep-detector 9,758, hep-citations 8,916,
hep-measurement 9,386, hep-ml 8,846, hep-statistics 10,797, hep-theory 9,622, hep-authoring 9,171,
hep-review 12,182 bytes. Keep new material in those index sections, not in `SKILL.md`. A change to what a skill
reads before it acts needs the routing checks (`check_routing_static.py`, `check_ownership.py`) and a live routing
rerun of the cases that involve the skill before it is merged (VALIDATION SKILL-TRIM shows the shape of that record).

## Porting a fix

1. Reproduce the defect with a failing test first.
2. Fix in the owning location: the general method in its owner skill or `core/` module (`core/OWNERS.json`);
   experiment or domain specifics in the profile. Never fix the same method in two places.
3. Commit scientific corrections separately with the `sci-fix:` prefix and the regression test; pure moves use
   `move:`. Never silently clip negative bins, repair covariance or response matrices, invent correlations, or change
   cuts, weights, binning, bounds or constants.

### Scientific corrections: scope and evidence

`sci-fix:` is for changes that alter a number, a verdict or status, or method guidance for a valid input
(severities S1 silently wrong number, S2 wrong verdict or status, S3 wrong guidance only). A change that turns a crash
or hang into a finding, or makes concurrent or interrupted runs safe without changing any result, is S4 and uses
`robust-fix:`; it still needs its regression test and parent record.

Evidence is graded on two axes, reported separately and never combined (vocabulary in
`docs/evidence/sci-fixes.json`):

- **Correctness (C):** is the new behavior right? C1 pinned values or behavioral assertions only; C2 one independent
  oracle kind; C3 two or more independent oracle kinds plus an invariant (property) test and a negative control;
  C4 exhaustive or symbolic over a stated finite domain. Independent kinds: exhaustive, symbolic, analytic, published
  (with a page, table or equation locator, pinned to the edition including errata), independent implementation.
- **Discrimination (D):** would the evidence have caught the defect? D1 a combined count or before/after values;
  D2 a per-test record that each evidence test failed on the parent commit and passes on the fix; D3 D2 plus local
  mutants of the changed function killed (at least the revert of the fix).
- **D scope (maintainer decision, 2026-10-22).** "Each evidence test" means each oracle node named by the entry's
  `independence` records: D2 needs, for every one of them, a parent record that fails on the parent and passes on
  the fix. When only other regression tests have parent records, the grade is at most D1 and `gaps` says so; an
  entry without independence records (C1) needs such a record for a regression test. A parent failure counts when
  the test reached the parent's code and failed by assertion, or by an exception that is the defect itself (a
  traceback on malformed input, a missing verdict); an import error, or a function, argument, input form or output
  key new in the fix, is a parent `error` and does not count. D3 additionally needs at least one killed `revert`
  mutant (one that restores the parent's code or behavior of a function the fix changed).

Minimum: S1 C3 and D2 (C4 where the domain is finite or a closed form exists); S2 C2 and D2; S3 a located source
and a second source; S4 C1 and D2.

The ledger and the advisories have JSON schemas in `docs/evidence/schemas/` (structure only, the keywords
`contracts/schema.py` implements, no `$ref`; `tests/tools/test_scifix_schemas.py`); cross-file rules stay in the
ledger test and `tools/scifix_advisories.py check`. They are not artifact contracts and do not move `CONTRACTS_VERSION`.

Transcription rule (maintainer decision 2026-10-22; reported by `tools/scifix_ledger.py report`, not yet enforced):
a C3 grade needs at least one independence record whose expected value is not computed from a formula transcribed
into the repository. Each record states `expected_from`: `printed` (a value printed in a source), `third-party-definition`
(another implementation's own algorithm or definition, not a library evaluating our formula), `exhaustive`,
`general-result` (a property any correct method has, such as a calibrated p-value's size), `person`, or
`transcribed-formula`. An entry with transcribed formulas only says so in `gaps`; the maintainer then decides between
more evidence and a lower grade.

A documentation fix lists its `sources` (`kind` external or internal, `citation`, `locator`, `read`); an S3 entry
below the minimum says what is missing in `gaps` (internal sources only are a gap, maintainer decision 2026-10-22).
An entry may carry a per-entry human sign-off, `review` `{by, date, scope}`: a person looked at the whole entry, unlike
an independence record's `basis: person` (a person checked one oracle's expected values). An agent review record is
not a sign-off. The report lists the S1 entries without one; every S1 entry is to be signed off before the next minor
release.

Oracle rules:

- An expected value is never copied from the code's output. Compute it in the test from a closed form, read it from
  a fixture transcribed from the source, or freeze an external tool's value with the tool and version stated.
- The oracle does not import the module under test or its private helpers. Two modules under test compared with each
  other, or a closure through the module's own helpers, is a consistency check, not an oracle.
- Independence means a different algorithm, specification source or author, and preferably two of them. When the fix
  was written with an AI assistant, an oracle the same assistant wrote counts as an independent kind only with one of
  four bases (maintainer decision, 2026-10-20): **locator**, its formula or rule cites a located source (paper,
  equation, table or page; a review section alone is not enough) that was read and is recorded in the repository;
  **third-party**, its expected values come from another implementation's own algorithm (scipy.stats, SymPy, ArviZ,
  pyhf, pathlib, Python's decimal rounding), not from a library evaluating a formula the assistant wrote;
  **exhaustive**, an enumeration over a stated finite domain; **person**, a person checked it and the record says so.
  Each counted kind is recorded in its entry's `independence` list (kind, test, basis, detail);
  `tests/tools/test_scifix_ledger.py` checks it. A `locator` record also names its source and located claim
  (`source_id`, `locator_id`: a string, or a list when it rests on several) in `docs/evidence/scifix-sources.json` and
  `scifix-claims.json`, the core/evidence format (index `scifix-index.md`); the source must be read at `page` or
  `full-text`. Every record states what its oracle test imports, `requires: {"core": [...], "backend": [...]}` (core:
  `requirements-core.txt` and sympy's mpmath; backend: pyhf, arviz, pdg, torch, xgboost, sklearn), and each backend
  must be locked by a required CI gate. `python3 tools/run_required_backends.py --from-ledger --no-skips` runs every
  oracle node and classifies each one that does not pass: a missing core dependency is an environment error, a
  missing backend leaves the evidence unverified, any other failure means the evidence does not hold. The weekly
  `ledger-evidence` job of `statistics-validation` runs it with every backend installed (pyhf, ArviZ, pdg).
- Kinds: **analytic**, an expected value derived in closed form; **independent implementation**, a different algorithm
  computing the same quantity; **symbolic**, a computer-algebra derivation; **published**, a value printed in a source;
  **exhaustive**, every case of a stated finite domain. Invariants, closures and behavioral checks are evidence, not
  independent kinds.
- A parent record from an adapted parent tree is D2 when the adaptation only adds modules the test imports (new in the
  fix) or guards an import, never the code under test, and the record says so. Copying the evidence test files
  (with their fixtures and test helpers) into the parent tree is the method, not an adaptation.
- Tolerances are fixed before the first run and justified (precision, grid step, Monte Carlo error); a failing
  check is never repaired by widening its tolerance.
- A negative control that emulates the pre-fix behavior inside the test is correctness evidence; it is not a parent
  record.
- Evidence that skips (an optional backend, the slow tier) is unverified, not passed: list such modules in the gate
  that requires the backend (`tools/run_required_backends.py`), or run them in the release gate.
  The required CI gates: `stats-backends` (pyhf, ArviZ, NumPy, hypothesis), `pdg-cross-check` (pdg),
  `torch-backend` (the hep-ml modules with PyTorch tests, torch pinned; `tests/tools/test_pyproject.py` checks that
  every such module is listed) and `bdt-backend` (the modules with xgboost or scikit-learn tests: `train_bdt.py`,
  `export_bdt.py` and the analysis-to-paper BDT path, with the `bdt` extra pinned, xgboost 3.4.1 and scikit-learn
  1.9.1 plus scikit-learn's joblib, narwhals and threadpoolctl; `tests/tools/test_pyproject.py` checks that every such
  module is listed and that the pins lie in the extra's ranges; a scikit-learn skip reason names `sklearn`, the import
  name the gate matches). The unpinned `optional (torch-cpu)` job is an early warning for new PyTorch releases: when
  it passes on a newer one, bump the `torch-backend` pins.

Record each correction in `docs/evidence/sci-fixes.json` and in `VALIDATION.md` with one row per evidence test.
The ledger entry carries the D axis as data: `commits` (`parent`, `fix`, `follow_up`: full 40-character hashes),
`parent_records` (`test` as file::Class::method; `parent` fail, pass, error or skip; `fix`; `failure` assertion,
error or null; `env`; `adapted_parent`, with `adaptation` only when true, `adds new modules` or `guards an import`;
`validation`, the VALIDATION.md section that holds the row; `requires` as for independence records) and `mutants`
as VALIDATION records them (`function`, a path or path::name; `mutation` revert or other; `killed_by`, the tests;
`detail`); `evidence_tests` lists the nodes of both. `tests/tools/test_scifix_ledger.py` recomputes D2 and D3 from
these records. One entry is one fix: an entry that bundled several is split, and its id stays as a tombstone in
`superseded` (`id`, `superseded_by`, `note`); advisories name the new entries.
The ledger's `changelog` names where the fix shipped: `{"kind": "release", "release": "X.Y.Z"}`, `{"kind": "audit",
"name": ..., "release": ...}` (a release section's audit subsection), or `{"kind": "unreleased"}` until the release
(an optional `detail` gives the item label); the release is a CHANGELOG section and, when an advisory names the entry,
the advisory's `fixed` release; an unreleased entry's advisory range is still open. An S1 or S2 entry is named by an
advisory or carries `advisory_waiver` `{reason, decided}` (for example: only the status of input that produced no
result changed). `regression_of` lists the entries whose fix introduced this defect; `scifix_advisories.py check`
warns when an advisory's `introduced_commit` is another advisory's `fixed_commit` until a person confirms the link
there (merge and squash commits can make it misleading; an over-correction inside one entry is a follow-up commit,
not a regression). A sci-fix that changes input normalisation (separators, signs, leading zeros, fractional parts,
path segments) comes with a property or exhaustive test, and its PR description lists the other callers of the
changed function and whether their input range changes (maintainer decision 2026-10-22, after SFA-2026-002 and
-003).

| Evidence test (file::Class::method) | Oracle kind | Parent commit result | Fix commit result | Skipped? | Environment |
|---|---|---|---|---|---|

A combined count ("8 of 20 fail") or before/after values without the tests is D1. Evidence files live inside the
plugin; an artifact outside it cannot be rerun.

Older records (VALIDATION.md, commit messages) name test folders as they were then; the history is not rewritten.
Under `tests/skills/`: `physics_ml/` is now `hep_ml/`, `detector_response/` is `hep_detector/`, `hep_analysis/` is
`hep_measurement/`, and `research_communication/` and `hep_communication/` are `hep_authoring/` (literature tests:
`hep_citations/`). A parent record names the path at the fix commit, where its test ran.

**Advisories (shadow mode).** A sci-fix that changed a released number or verdict gets an advisory,
`docs/evidence/advisories/SFA-YYYY-NNN.json` (numbers never reused; `README.md` there lists the gaps; OSV
`published` and `modified` UTC timestamps; format `hep-research-scifix-advisory/2`, provisional; the scan reads `/1` for one more release), for people who
hold results made before the fix. It names the ledger entries instead of repeating the evidence, gives the affected
plugin files and an OSV `SEMVER` range (`introduced`, then `fixed` or `last_affected`; no closing event while the fix
is unreleased, with `database_specific.fixed_commit`), the scientific impact apart from the range (`observables`,
`bias`, `trigger`), which artifacts it touches (`applies_to`, below) and a `remedy`. At the release that ships a fix, add its `fixed` event. `tools/scifix_advisories.py`:
`check` validates every advisory against the ledger, the plugin tree and the release manifests
(`tests/tools/test_scifix_advisories.py` runs it): X.Y.Z versions, no two events at one version, each `fixed` above
its `introduced`; a `fixed` release changes an affected file against the release before it; an `introduced` release
that already held an affected file states `database_specific.introduced_basis`; artifact types from the contracts'
vocabulary; and match conditions that discriminate. `applies_to.match` is OR over groups, AND within a group, of
conditions `{path, op, value | values, unknown_before}`: `path` joins envelope keys with `.` and `[*]` expands a list
(`extension.tools[*].name`); `op` is `exists` (present, not null and not a missing marker), `eq`, `in` or `regex`. A
condition is undecided when the artifact cannot show it: a trace path (`provenance.code_paths`, `code_tags`) on an
artifact without that field (written before contracts 3.5.0), or a `contract_version` below `unknown_before` (the field
did not exist yet). A group that holds makes the artifact affected; when none holds and one is undecided, or when
`match` is `[]` (no field can show that the affected code ran; `match_basis` says why), it is possibly affected (no
trace), named by `no_trace`. Every group needs a discriminating condition: anything but `exists` on a top-level
extension key that every artifact of a listed type carries. Write conditions from what the affected code writes into
the artifact; the trace holds the code the writer's process loaded, plus a core/stats CLI's own trace when
`result_artifact.py` wraps its output (a training asset runs elsewhere and is not traced). When the affected code writes output that is no artifact, give `applies_to.outputs` (`producer` files and
`how_to_recognize`); the scan lists it apart, and `artifact_types` may be `[]` when no artifact can show the code ran.
`affected` lists the releases in range that hold an affected file,
from `release-manifests/` (a file moved between skill folders is found by its path below the folder); `scan
PROJECT_DIR` reports, read-only, which of a project's artifacts an advisory touches, with the release that made each
(`digest-consistent`, formerly `verified`, when the `versions.plugin_release` digest equals that release's manifest;
claimed; or unknown; a build between releases claims the last release, so it is only possibly affected). Per
advisory the scan decides in order: `outputs` are listed apart (`outputs_not_artifacts`); then the artifact type,
the match (affected, or possibly affected (no trace)), the release range, and
whether that release's manifest holds an affected file; a missing marker (`unknown`, `not-applicable`, `not-provided`) in
a key is absent, not a sign that the code ran. Shadow mode: the scan exits 0 whatever it finds and blocks nothing.

**Execution trace (contracts 3.5.0; maintainer decision 2026-10-22, revising "no `provenance.producer` field").**
Its premise, that the artifact type and extension keys show which code path ran, did not hold: eleven advisories keyed
on fields every artifact of the type carries, and eight affected scripts write no artifact at all (sci-fix improvement
plan F-01, F-02, F-27). An envelope writer adds `**trace.provenance()` (`contracts.trace`, implemented in `core/trace.py`) to `provenance`:
`code_paths`, the plugin `.py` files loaded when the envelope was written (loaded, not executed; the test suite left
out), and `code_tags`, the tags that shared functions named by an advisory set with `trace.tag()`, cleared per envelope.
Code that runs in another process is not in the writer's own trace. The core/stats CLIs print theirs as `trace`
(`{code_paths, code_tags}`) in their JSON output, and `result_artifact.py` joins it to the statistical-result it
writes; a training asset or another subprocess is not traced, so an advisory about such code matches on fields
that code writes, or says that no field can show it. Artifacts older than 3.5.0 carry no trace.

## Rerunning comparisons and examples

Each example writes byte-reproducible output with its seed and tolerances; run `python3 examples/<name>/run.py`
from the plugin root (each takes `--help`; the seeds are in each `output/report.md`). The researcher journey each one exercises:

| Example | Journey |
|---|---|
| `examples/ams-flux-ratio/` | J1 |
| `examples/detector-resolution/` | J2 |
| `examples/collider-angular/` | J3 |
| `examples/qed-prediction/` | J4 |
| `examples/theory-comparison/` (run after B and C) | J5 |
| `examples/published-comparison/` | J6 |
| `examples/recasting/` | J7 |
| `examples/local-partition/` | - |
| `examples/batch-partition/` (fake Slurm and HTCondor schedulers) | - |
| `examples/end-to-end-sample/` | - |
| `examples/unfolding-coverage/` | J3 |
| `examples/analysis-to-paper/` (E-4: score, cut, template fit, result artifact, rendered macros, draft, HEPData; `--with-bdt`, `--root-python` optional) | - |
| `examples/bc-fragmentation/` (E-1: coupled feed-down, survival in material, species-migration blocks, joint fit) | - |
| `examples/multi-era-fit/` (E-3: two eras, collection time, era responses, split consistency, joint fit, S2 projection) | - |
| `examples/pbar-p-curvature-offset/` (E-2: a curvature offset in one era, its ratio shift, its ledger entry and its fit) | - |
| `examples/stats-benchmarks/<name>/` (hep-statistics audit benchmarks: `coverage-grid`, ...; `--toys` sets the budget) | - |
| `examples/geant4-thin-silicon/` (offline replay of recorded Geant4 11.4.3 runs; `--live` reruns them) | J14 |
| `examples/design-minimal-spectrometer/` (offline replay of the recorded J15 campaign; `live.py` reruns it) | J15 |
| `examples/design-search-j16/` (searches on Examples A and B; offline replay of the recorded Example A confirmation; `live.py` reruns it) | J16 |

`tests/examples/` compares a fresh run with the
committed output. When a change alters a committed number, explain why in the commit, regenerate the output, and
record the old and new values; a change beyond the declared tolerance is a breaking change.

## Evidence ledgers

Update sources and claims through the ledger files, keep ids stable (renaming an id is breaking), set the
verification date to the day the source was read, then run `core/evidence/ledger.py` and regenerate the index with
`core/evidence/render_index.py`.

## Schema migration

Contracts carry `CONTRACTS_VERSION` (`contracts/__init__.py`) and each artifact records the plugin, contract and
profile versions it was written with. Adding an optional field or vocabulary term is a minor change. Removing or
renaming a field, changing a default convention, or tightening a rule so old artifacts fail is a major change and
needs: a converter that rewrites old artifacts with explicit refusal codes for what it cannot convert, valid and invalid
fixtures in `contracts/fixtures/`, and an entry in the changelog of the release.

Readers apply a version policy (`contracts/validate.py`, since 2.1.0): a newer major is an error; a newer minor is a
warning, or an error with `--strict-versions` or in protected mode (`--protected`, or a project with
`agent_policy`); `versions.contracts` must equal `contract_version`; an unknown entry in
`required_capabilities` is an error (add new capabilities to `contracts.KNOWN_CAPABILITIES` when a reader implements
them). `contracts/dependencies.py` validates every source the same way. Skill names (contracts 3.0.0): only the names in
`contracts/skill_names.py` (`SKILLS`) and `contracts/schemas/skill_names.json` are valid. A name retired in 0.17.0 (the
deprecated aliases of the 0.11.0 rename and the 0.16.0 split) in `provenance.producer_skill`, `handoff.to_skill`, an
extension `handoff` or a profile's `related_skills` is an error, `skill.unknown_name`, whose message says to migrate the
file with hep-research 0.16.x (its `contracts/migrate_skill_names.py`); any other unknown `handoff.to_skill` is the same
error. The retired names are kept only as SHA-256 hashes; `tools/check_retired_names.py` fails on any maintained file
that spells one (history files excepted). When a skill is renamed, keep the old name as a deprecated alias for at least
one release, with a migration tool, before retiring it in a major contract version. Artifacts record the code identity in
`versions.plugin_release` through `contracts/identity.py`; older artifacts lack it and their identity is unknown.

Communication records come in two formats. A legacy record (claims with `result_ref` and a status) stays valid and
readable; project resolution (`contracts/communication_project.py`) reports it as *limited traceability*: only the
envelope inputs resolve, no claim is linked to an evidence edge, an occurrence or an assessment, and the record is
never called fully traced. The traceability format is selected by `required_capabilities:
["communication:traceability-v1"]` with `traceability_version: "1.0.0"` in the extension; there is no automatic
migration, because the ids, evidence locators, read events and verdicts it needs are facts a reader supplies, not
values a converter may invent. A legacy record is migrated by writing a new record in the traceability format next to
it, with deterministic local claim ids and every unknown mapping left in `unresolved_inputs`.

## Versioning

SemVer for the plugin (`.claude-plugin/plugin.json`), contracts, core (`core/__init__.py`), each profile and each
ledger. A profile states the core and contract ranges it supports (`compatible`); the registry check rejects an
incompatible pair. Projects pin a plugin range in `hep-research.project.json`.

## Adapter changes

Follow `docs/adapter-authoring.md`: bump the adapter version, rerun its tests in the declared environment, update
`adapter.json`, `VALIDATION.md` and the capability matrix.

## Adding a topic

A topic is a reference page, a script, or both, in a skill. `tools/check_wiring.py` (run by `run_all_checks.py`
without `--since`) checks the hand-kept lists it must enter: every page one step from the `SKILL.md` Resources table
or the entry reference's routing part, or two steps through a hub registered in `tools/wiring_known_gaps.json` (R1);
the CLI dictionaries of `tests/skills/test_cli_robustness.py` (R2); the counts in each skill README (R3); and, with
`--since`, the CHANGELOG (R4). It exits 1 only on a gap that file does not list; the file only shrinks.

1. Add the page or script.
2. Run `python3 tools/check_wiring.py --since <base>` (the commit you started from).
3. Following its report, add a Resources row or a link in a registered hub page (prefer the hub: the entry
   reference counts towards the 25,600-byte quick-load budget, and its routing part towards the 4 KB soft limit;
   never change the first row of a Resources table), the README count, the script's entry in `MISSING_FILE_ARGS` or
   `NO_INPUT_FILE`, and a CHANGELOG line under `## Unreleased` (a capability-matrix row only for a new id in
   `docs/capability-map.json`). A page that routes one topic may be registered as a hub when it is itself one step
   away. A moved page leaves a pointer titled "... (moved)" for one minor release; record the release that removes it
   under `pointers`.
4. Regenerate: `python3 tools/reference_inventory.py`, `python3 tests/routing/make_cases.py`, and
   `python3 tools/capability_map.py --write` when the capability map changed.
5. Run `PYTHONDONTWRITEBYTECODE=1 python3 tools/run_all_checks.py --part static` (about 50 s) and the affected unit
   tests; `python3 contracts/rule_registry.py impact <path> ...` shows what CI will run for the changed paths.

When a fix clears a known gap, delete its entry (`tests/tools/test_check_wiring.py` fails on a stale one).

## Routing

`tests/routing/cases.json` is generated by `tests/routing/make_cases.py`; `tools/check_routing_static.py` checks it
against the descriptions. A change to a skill description should be followed by a live routing run (paid model
calls, run only with approval); the G5 record in the source repository shows how it was done.

The [capability map](capability-map.md) is edited in `docs/capability-map.json`; regenerate its table with
`python3 tools/capability_map.py --write`. A domain outside v1 on the map needs a limited-support routing case routed to
its owner, which `check_routing_static.py` checks.
