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
`tools/budget_exceptions.json` may waive; above 16,384 bytes or 500 lines it fails, with no exception. A description
stays at or under 1,024 characters, the limit of the [Agent Skills specification](https://agentskills.io/specification),
and the profile registry at or under 3,072 bytes (`REGISTRY_BUDGET` in `contracts/registry.py`). Until 2026-10-17
the budget was 8,192 bytes per `SKILL.md`. On 2026-10-13 the three files that sat at the limit were trimmed by moving their reference and script lists into index
sections of their primary reference (`hep-detector`: section 11 of the principles summary; `hep-statistics`:
"Skill scripts" in the core/stats guide; `hep-computing`: "Scripts" in the engineering playbook); they now measure
6,566, 7,545 and 7,598 bytes. Measured on 2026-10-17 (upgrade batch 0b, after the routing tables of B-02, `tools/measure_entrypoints.py --no-cli`):
hep-communication 9,322, hep-computing 8,767, hep-detector 8,771, hep-measurement 8,918, hep-ml 7,895,
hep-statistics 9,257, hep-theory 8,341 bytes. Keep new material in those index sections, not in `SKILL.md`. A change to what a skill
reads before it acts needs the routing checks (`check_routing_static.py`, `check_ownership.py`) and a live routing
rerun of the cases that involve the skill before it is merged (VALIDATION SKILL-TRIM shows the shape of that record).

## Porting a fix

1. Reproduce the defect with a failing test first.
2. Fix in the owning location: the general method in its owner skill or `core/` module (`core/OWNERS.json`);
   experiment or domain specifics in the profile. Never fix the same method in two places.
3. Commit scientific corrections separately with the `sci-fix:` prefix and the regression test; pure moves use
   `move:`. Never silently clip negative bins, repair covariance or response matrices, invent correlations, or change
   cuts, weights, binning, bounds or constants.

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
them). `contracts/dependencies.py` validates every source the same way. The same flag carries the name policy
(contracts 2.9.0, "version and name policy"): a deprecated skill name (the four names renamed in 0.11.0, listed in
`contracts/skill_names.py` and `contracts/schemas/skill_names.json`) in `provenance.producer_skill`, `handoff.to_skill`
or an extension `handoff` is a warning (`skill.deprecated_name`), an error with `--strict-versions` or in protected
mode; in a profile's `related_skills` it is `profile.deprecated_skill_name` (`contracts/registry.py
--strict-versions`). `contracts/migrate_skill_names.py OLD.json --out NEW.json` rewrites `producer_skill` and
`to_skill` and nothing else. The aliases are removed one or two releases after the rename. Artifacts record the code identity in
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

## Routing

`tests/routing/cases.json` is generated by `tests/routing/make_cases.py`; `tools/check_routing_static.py` checks it
against the descriptions. A change to a skill description should be followed by a live routing run (paid model
calls, run only with approval); the G5 record in the source repository shows how it was done.

The [capability map](capability-map.md) is edited in `docs/capability-map.json`; regenerate its table with
`python3 tools/capability_map.py --write`. A domain outside v1 on the map needs a limited-support routing case routed to
its owner, which `check_routing_static.py` checks.
