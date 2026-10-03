# TASK: Add Slurm and HTCondor batch execution to the `hep-research` plugin

> **For Claude (agent):** This file is an executable work order. Read it fully before changing any file. Follow the
> Execution Rules, finish Phase 0 before any task, work through the tasks in the stated order, and end with the Final
> Report. Unless noted otherwise, every path is relative to `plugins/hep-research/`. Suggested location in the
> repository: `tasks/hep-research/batch-schedulers/TASK.md`.

> **Revision r2 (2026-10-03).** Checked against `main` at `ae2b4d2` (PR #13 merged, contracts 1.1.0) before
> execution. Changes from r1 are listed in §10 and marked `(r2)` in place; everything else is unchanged.
>
> **Revision r1 (2026-10-03).** Written from an inspection of the uploaded ZIP `hep-research-main.zip` (commit not
> recorded in the ZIP). Evidence labels follow `tasks/hep-research-plugin.md` §2.2: `[Confirmed]` read in the
> repository, `[Inferred]` a conclusion from confirmed facts, `[Proposal]` a design choice open to change,
> `[To verify]` a tool fact (option name, output format, state code, version behavior) that must be checked against
> the installed tool's documentation or a real run before it is written into the plugin.

---

## 0. Context

| Item | Value |
|---|---|
| Repository | <https://github.com/hchouTW/hep-research> |
| Plugin / contracts version | `0.1.0` / `1.0.0` `[Confirmed]`; (r2) contracts are `1.1.0` on `ae2b4d2` (PR #13), `computational-run` unchanged |
| Owner skill | `hep-computing` (SKILL.md 56 lines, 6,788 B; description 859 of 1,024 chars) `[Confirmed]` |
| Tools in scope | Slurm and HTCondor, both workload managers and job schedulers |

### 0.1 What already exists

All `[Confirmed]`.

- **Ownership.** `tasks/hep-research-plugin.md` §7.2 gives "partition/merge" and "manifests" to `hep-computing`. `skills/hep-statistics/SKILL.md` hands "large toy campaigns, batch partitioning" to `hep-computing` with a `computational-run` artifact.
- **The promise in the description.** The `hep-computing` description already says "partitioning, batch submission, merging and recovery". Two routing cases test that phrase: one English, one zh-Hant, in `tests/routing/cases.json`.
- **A local engine.** `skills/hep-computing/scripts/local_partition.py` (standard library only) enforces the rules a batch backend must keep:
  - a manifest with per-chunk seeds, tied to outputs by a hash;
  - atomic, write-once chunk outputs, with finished chunks skipped on resubmission;
  - retries only when `max_attempts` is configured;
  - a stop after two identical failures;
  - state kept on disk;
  - an explicit `reset` with a reason;
  - a merge that requires every chunk exactly once, with ranges tiling `[0, n)`.

  Example: `examples/local-partition/run.py`; test: `tests/examples/test_local_partition.py` (T21); capability matrix row "Local partition, resubmission, merge: tested (E1)".
- **Invariants in `hep-computing`.** No retries without a configured maximum; repeated identical failures stop; scripts emit an exit code plus JSON status; nothing is installed or fetched without approval.
- **Contracts.** `computational-run` (`contracts/schemas/ext_computational_run.json`) requires inputs with sha256, tools with versions, commands, environment, seeds, tolerances, exit status and output hashes, and has a free `resources` object. A non-zero exit status must carry `failed` (`contracts/validate.py`).
- **Adapter rules** (`docs/adapter-authoring.md`). A tool status above `documented` needs tests that run the tool in a declared environment, and the adapter status is the lowest of its tools' statuses (enforced by `tests/adapters/test_adapter_declarations.py`). The main spec §7.12 already lists "batch schedulers" as a candidate adapter, `proposed` until executed.
- **Layering** (`tools/check_layering.py`). `adapters/*` may import only `core` and `contracts`, never a skill script. `core/OWNERS.json` admits code into `core/` only when more than one top-level component uses it.
- **Loop guardrails** (`skills/hep-computing/references/loop-engineering.md`). A loop that observes external state and acts must name its pattern and fix its termination condition, maximum-iteration limit, and early stop.

### 0.2 Why this task exists

| # | Finding | Evidence |
|---|---|---|
| F1 | The repository has **no** Slurm or HTCondor content: no reference, script, adapter, template or test (grep for `slurm`, `htcondor`, `condor_`, `sbatch` finds nothing). The `hep-computing` description promises "batch submission" and two routing cases route to it, but the skill has nothing to apply. | `[Confirmed]` |
| F2 | `local_partition.py` runs chunks **synchronously in-process** (`run(manifest, state_dir, worker)`). On a cluster, chunks run remotely and asynchronously. They can run twice (eviction, requeue, a lost-then-found job), and they finish out of order. The local design cannot be reused as is. | `[Confirmed]` code; `[Inferred]` consequence |
| F3 | A scheduler adapter cannot import the partition logic from `skills/hep-computing/scripts/` (layering). Sharing it requires moving it to `core/` under the admission rule. | `[Confirmed]` |
| F4 | Both schedulers can **retry or restart jobs on their own**. This silently breaks the plugin's "no retries without a configured maximum" and "write once" rules unless the adapter disables the automatic behavior or accounts for it. Examples: Slurm requeue; HTCondor eviction and restart, `max_retries`, `on_exit_remove`. | `[Inferred]`; tool behavior `[To verify]` |

### 0.3 Design constraints to preserve

- The manifest, write-once, bounded-retry and complete-merge semantics of T21 stay exactly as they are; the local path
  stays standard library only, and its example output stays byte-identical.
- **Seeds come from the manifest, never from a scheduler index or job ID**, which change on resubmission.
- Nothing scheduler-specific becomes mandatory. The adapter is optional, and every existing path works without it.
- **Site facts are never invented.** Partition or pool names, accounts, QoS, memory and time limits, GPU types, and file
  systems come from user or project configuration. When required keys are missing, the tool refuses with a named
  error; it does not fall back to a guessed default.
- Execution success is not scientific validity. A complete merge says nothing about physics correctness.

---

## 1. Execution Rules

1. **Never act on a real cluster without explicit, per-action user approval.** That covers submitting, cancelling,
   releasing or removing jobs, and writing to shared areas. During development use the fake-scheduler shims (S08) or
   a disposable local Slurm or HTCondor installation the user approved (Q1). Every command that changes scheduler
   state defaults to **dry-run** and needs an explicit flag (for example `--submit`).
2. **No network access or installation without approval** (`tasks/hep-research-plugin.md` §2.1, §13.3). Missing
   tools make tests **skip**, and a skip is unverified, never passing.
3. **Regression test first** for every behavior change. The S01 move must reproduce T21's committed output byte for
   byte.
4. **Every tool fact is checked before it is written into the plugin.** That covers each option, state code and output
   format, checked against the documentation of the version actually used (record the version and date) or against a
   real run. Items marked `[To verify]` below are design intent, not facts.
5. **Fail closed.** An unknown scheduler state, an unparsable output, a missing accounting record, or a job that
   disappears with no output is reported as `unknown` / `lost` / `incomplete`, with a non-zero exit code. It is never
   treated as success or silently retried.
6. **Commits:**
   - one task or step per commit, with the ID in the message: `move(B01): …`, `feat(B04): …`, `docs(B10): …`;
   - moves separate from behavior changes (`docs/maintenance.md`).
7. **English** for every file, commit and report (`tasks/hep-research-plugin.md` §2.6); routing fixtures keep their
   en + zh-Hant mix.
8. **Stay in scope** (§5). Escalate the stop conditions of `tasks/hep-research-plugin.md` §13 (installs, three failed
   attempts, a site fact nobody provided).

---

## 2. Phase 0 — Baseline

Run from `plugins/hep-research/`; record every result.

```bash
python3 -m unittest discover -s tests -t .
python3 tools/run_all_checks.py --out /tmp/batch-r0
python3 tools/check_layering.py
python3 tools/measure_entrypoints.py --no-cli
python3 examples/local-partition/run.py --out /tmp/t21 && sha256sum /tmp/t21/results.json examples/local-partition/output/results.json
```

- [ ] Record the commit hash and the Python and core package versions. Record whether `sbatch`, `sacct`, `squeue`,
  `condor_submit`, `condor_q` or `condor_history` are on `PATH` (expected: none).
- [ ] Confirm F1 (grep), F2 (read `run()`), F3 (attempt an adapter-to-skill import in a scratch copy and show that
  `check_layering.py` rejects it) and the T21 checksum match.
- [ ] If any premise does not hold, record it and adjust the affected task before starting.

---

## 3. Task List

Priority:

- **P1:** needed for a correct, safe first version.
- **P2:** completes provenance, privacy and documentation.

| ID | Pri | Task | Finding |
|---|---|---|---|
| B01 | P1 | Move the partition engine to `core/partition` behind an executor interface | F2, F3 |
| B02 | P1 | Remote chunk protocol: worker-side runner, collection, duplicate safety | F2 |
| B03 | P1 | Normalized job states, failure classes and bounded resubmission | F4 |
| B04 | P1 | Slurm backend | F1 |
| B05 | P1 | HTCondor backend | F1 |
| B06 | P1 | Monitoring loop with explicit limits | F1 |
| B07 | P1 | Configuration schema: site facts from the user, never defaults | F1 |
| B08 | P1 | Fake-scheduler test harness with fault injection; real-tool tests in a declared environment | F1, F4 |
| B09 | P2 | Provenance: `computational-run` from a batch campaign | F1 |
| B10 | P1 | Reference: `batch-scheduling.md` (Slurm and HTCondor side by side) | F1 |
| B11 | P2 | Example `examples/batch-partition/` | F1 |
| B12 | P2 | Privacy and blinding: logs, site data, credentials | F1 |
| B13 | P1 | Integration: adapter declaration, SKILL.md, routing, VALIDATION, capability matrix, changelog | all |

**Execution order:** B01 → B02 → B03 → B07 → B08 (shims) → B04 → B05 → B06 → B09 → B12 → B10 → B11 → B13.
The real-tool part of B08 runs only if Q1 is approved.

---

### B01 (P1) — `core/partition` with an executor interface

**Files:**

- new `core/partition/` (steward `hep-computing` in `core/OWNERS.json`)
- `skills/hep-computing/scripts/local_partition.py` becomes a thin CLI over it
- `tests/core/test_partition.py`

**Implement:**

- [ ] Move manifest creation, state handling, `reset`, `status`, `merge` and the atomic write into `core/partition`,
  unchanged in behavior. This is a `move:` commit.
- [ ] Define an executor interface `[Proposal]`:
  - `prepare(manifest, chunk_ids, config) -> SubmissionPlan`, which is pure and has no side effects;
  - `submit(plan) -> list[SubmissionRecord]`;
  - `poll(records) -> list[NormalizedState]`;
  - `cancel(records)`.

  The existing synchronous behavior becomes `LocalExecutor`.
- [ ] The state file gains a per-chunk list of attempts (r2: named `attempt_records`, because the existing state already uses `attempts` for an integer count; §10 R3) (`attempt_id`, backend, scheduler job ID, submit time, final
  normalized state, error signature). Old state files without it are still read. Record the compatibility rule in
  `DECISIONS.md`.

**Acceptance:**

- [ ] `examples/local-partition/run.py` output is byte-identical to the committed `results.json`; T21 passes unchanged.
- [ ] `local_partition.py --help` and every CLI subcommand behave as before (existing tests pass untouched).
- [ ] `tools/check_layering.py` passes; `core/OWNERS.json` lists the module with its two consumers.

---

### B02 (P1) — Remote chunk protocol

**Files:**

- new `core/partition/runner.py` (runs on the worker node; standard library only)
- collection logic in `core/partition`
- tests in `tests/core/test_partition_remote.py`

**Implement:**

- [ ] **The runner.** It receives the manifest path or content, the chunk ID and the attempt ID. A scheduler array index
  maps to a chunk ID only through a submission map written at submit time, and seeds come from the manifest. The runner:
  - runs the user command with `{start} {stop} {seed} {out}` substitution, as in `local_partition.py run --cmd`;
  - writes the result to a temporary file in the destination directory, then renames it, so the write is atomic on the same file system;
  - records `chunk_id`, `manifest_hash`, `attempt_id`, host name, start and end time, exit code, and the environment fingerprint (Python version, container image if declared).
- [ ] **Collection.** It validates every candidate output: manifest hash, chunk ID in manifest, schema, finite numbers.
  - Duplicates of a chunk (eviction, requeue, a resubmission racing a late original) are recorded as `duplicate`, and only one is ingested, chosen by a declared rule `[Proposal: first valid by attempt order]`. They are never summed.
  - A foreign or corrupt output is quarantined with a reason, never deleted silently.
- [ ] **Shared file system vs file transfer.** Both are supported. With HTCondor file transfer, outputs are remapped into a
  staging directory before collection (B05).

**Acceptance:**

- [ ] With an injected double run of one chunk, the merged result equals the single-run result exactly, and the
  report lists one duplicate.
- [ ] An output with a different `manifest_hash` is quarantined; the merge stays `incomplete` until the chunk is redone.
- [ ] A truncated or partial file (no rename happened) is never collected.

---

### B03 (P1) — Normalized states, failure classes, bounded resubmission

**Files:** `core/partition` (state model); tests.

**Implement:**

- [ ] **Normalized states:** `planned`, `queued`, `running`, `done`, `failed`, `timeout`, `out-of-memory`,
  `preempted-or-evicted`, `node-failure`, `held`, `cancelled`, `lost`, `unknown`. Each backend maps its native states
  to these (B04, B05). Unmapped native states become `unknown`.
- [ ] **Retry classes** `[Proposal]`:
  - Retryable within `max_attempts`: `preempted-or-evicted`, `node-failure`, `lost` (only after confirming no valid output exists).
  - Retryable only after a resource change recorded in the attempt: `timeout`, `out-of-memory`.
  - Never automatically retried: `failed` (exit code not 0), `held`, `cancelled`, `unknown`. These need `reset` with a reason, the existing rule.
- [ ] **Error signatures** for the "two identical failures stop" rule are normalized (state + exit code + signal + hold
  reason code). Host names and timestamps stay out of the signature, so a deterministic bug stops after two attempts
  on different nodes.
- [ ] Resubmission happens only through an explicit `resubmit` command and only for chunks that are not done. With no
  `max_attempts` configured, nothing is resubmitted (unchanged rule).
- [ ] **Scheduler-side automatic retries are disabled in generated job descriptions, or, where a site forces them, counted as
  attempts.** Slurm: no requeue; HTCondor: no `max_retries`, default exit handling. Option names and site overrides
  are `[To verify]`.

**Acceptance:**

- [ ] A parametrized test covers each normalized state with its retry decision.
- [ ] A chunk that fails twice with the same exit code on two different hosts stops with `stopped-repeated-failure`.
- [ ] Without `max_attempts`, a campaign with failures performs zero resubmissions and exits non-zero with the failed
  chunks listed.

---

### B04 (P1) — Slurm backend

**Files:**

- new `adapters/batch-schedulers/slurm.py` (r2: `slurm_backend.py`, see §10 R4)
- template `adapters/batch-schedulers/assets/slurm-array.sbatch.template`
- tests

**Implement** (every option and format is `[To verify]` against the Slurm version used):

- [ ] **`prepare`.** Render one array job script per submission:
  - array range with a throttle from config (`--array=0-N%M`);
  - resources from config only: partition, account, QoS, time, memory, CPUs, GPUs/gres, constraint;
  - output and error paths under the campaign directory;
  - requeue disabled;
  - a `--parsable` submit.

  The script calls `core/partition/runner.py` with the chunk ID taken from the submission map using the array task index.
- [ ] **`submit`.** Only with an explicit submit flag; capture the job ID; record the exact command line.
- [ ] **`poll`.**
  - Use accounting (`sacct` with parsable, no-header output and an explicit field list: job ID, state, exit code, elapsed, max RSS, node list) and parse `ExitCode` as `exit:signal`.
  - When accounting is unavailable, fall back to the queue listing plus the presence of output files. Mark the result `incomplete` evidence rather than `done` for jobs absent from both.
  - Map states (for example COMPLETED, FAILED, TIMEOUT, OUT_OF_MEMORY, CANCELLED, NODE_FAIL, PREEMPTED, PENDING, RUNNING, REQUEUED) to B03's normalized states. The set and spelling are `[To verify]`.
- [ ] **`cancel`.** Only with explicit approval; record it.

**Acceptance:**

- [ ] Against the shims (B08):
  - each native state maps as specified;
  - an array of 10 chunks with a throttle of 3 produces exactly one submission with the expected script text (golden file);
  - dry-run makes no scheduler call (the shim call log is empty).
- [ ] Missing required config keys (partition and time at least `[Proposal]`) refuse with exit 2 and the key names.
- [ ] Real-tool test (if Q1 approved): a single-node Slurm runs the B11 synthetic campaign to a complete merge equal
  to the local result.

---

### B05 (P1) — HTCondor backend

**Files:**

- new `adapters/batch-schedulers/htcondor.py` (r2: `htcondor_backend.py`, so it never shadows the HTCondor Python bindings package `htcondor`; §10 R4)
- template `adapters/batch-schedulers/assets/htcondor-chunks.sub.template`
- tests

**Implement** (every command, macro and code is `[To verify]` against the HTCondor version used):

- [ ] **`prepare`.** Render a submit description:
  - one cluster per submission, with `queue` over the chunk IDs as item data, so each process gets its chunk ID directly;
  - `request_cpus`, `request_memory`, `request_disk` and GPUs from config;
  - universe and container image from config;
  - a job event log file for monitoring;
  - file transfer settings from config (shared file system or transfer, with output remaps into the staging directory);
  - no `max_retries`, default exit handling;
  - requirements only from config.
- [ ] **`submit`.** Only with an explicit flag; capture the cluster ID (terse output); record the command line.
- [ ] **`poll`.**
  - Prefer the **job event log** (submit, execute, evicted, held, released, terminated with exit code or signal), because it survives the job leaving the queue.
  - Fall back to queue and history queries with JSON output.
  - Map JobStatus and events to B03 states: idle → `queued`, running, completed, removed → `cancelled`, held → `held` with the hold reason and code, eviction → `preempted-or-evicted`, terminated by signal → `failed` with the signal.
  - A held job is reported with its reason and is **never released automatically**.
- [ ] **`cancel`.** Only with explicit approval.

**Acceptance:**

- [ ] Against the shims:
  - a job event log fixture with an eviction followed by completion yields one `done` chunk with two attempts recorded and no duplicate ingestion;
  - a held job yields `held` with its reason and blocks the merge as `incomplete`;
  - dry-run makes no scheduler call.
- [ ] Missing file-transfer or shared-file-system choice in config refuses with exit 2.
- [ ] Real-tool test (if Q1 approved): a personal HTCondor pool runs the B11 campaign to a complete merge equal to the
  local result.

---

### B06 (P1) — Monitoring loop with explicit limits

**Files:** `core/partition` CLI or `adapters/batch-schedulers/cli.py`; tests.

**Loop pattern:** an observe → decide → act control loop (ReAct-style, per
`skills/hep-computing/references/loop-engineering.md`).

1. Observe: poll the backend.
2. Decide: per chunk, from B03's rules, carrying the actual native state and error text into the decision record.
3. Act: only `collect`. Resubmission is not part of the loop unless `auto_resubmit` is explicitly configured,
   together with `max_attempts`.

**Implement:**

- [ ] `status` performs **exactly one poll** and exits. This is the default.
- [ ] `watch` runs only when the config gives `poll_interval_s` and at least one of `max_polls` or `deadline`. With
  neither, it refuses with a named error. The ceiling is never invented. Enforce a minimum interval
  `[Proposal: 60 s]`, so the scheduler is not hammered.
- [ ] **Termination:** all chunks terminal (`done` or stopped).
- [ ] **Early stop:** any `held`, `unknown` or `stopped-repeated-failure` chunk, a poll error repeated twice with the
  same signature, or the deadline. Each stop reason is reported.
- [ ] **Maximum-iteration limit:** `max_polls`. Exceeding it is reported as `incomplete`, not silently continued.

**Acceptance:**

- [ ] A forced test with a chunk stuck in `queued` stops after exactly `max_polls` polls and reports `incomplete`
  with the stuck chunk.
- [ ] `watch` without limits exits 2 and makes no poll.
- [ ] A shim that returns malformed output twice stops the loop with the parse error text in the report.

---

### B07 (P1) — Configuration: site facts from the user

**Files:**

- new `adapters/batch-schedulers/assets/batch-config.example.json` (placeholders only)
- validation in the adapter
- documentation in B10

**Implement:**

- [ ] **One JSON config per campaign:**
  - backend (`slurm` or `htcondor`);
  - resources per job: CPUs, memory, time or disk, GPUs;
  - site keys: partition, account, QoS, constraint for Slurm; requirements, universe, container image, transfer mode for HTCondor;
  - throttle;
  - `max_attempts`;
  - monitoring limits (B06);
  - campaign directory.
- [ ] Required keys per backend are validated with named errors. Unknown keys are rejected, not ignored. Values are
  echoed into the provenance (B09).
- [ ] The config lives in the user's project, never in the plugin. The example file contains only obvious placeholders,
  and the packaging check (B12) proves it.
- [ ] A **pilot mode** submits one chunk and reports its elapsed time and peak memory, so the user can size the rest.
  The tool never resizes requests on its own.

**Acceptance:**

- [ ] Fixtures for each missing required key, an unknown key, and a negative or zero resource refuse with exit 2.
- [ ] The example config validates as an example (placeholders accepted only with a `--example` flag) and fails
  without it.

---

### B08 (P1) — Test harness: fake schedulers and real-tool tests

**Files:**

- new `tests/adapters/batch_shims/` (executable fake `sbatch`, `squeue`, `sacct`, `scancel`, `condor_submit`, `condor_q`, `condor_history`, `condor_rm`)
- `tests/adapters/test_batch_slurm.py`
- `tests/adapters/test_batch_htcondor.py`

**Implement:**

- [ ] The shims run jobs locally in subprocesses and emit output in the documented formats of the targeted versions.
  Each format sample is copied from the tool's documentation or from a real run, and its source and version are
  recorded in a comment (`[To verify]`).
- [ ] Fault injection by environment variable: fail with exit code N, time out, run out of memory, evict then restart,
  hold with a reason, node failure, job vanishes, accounting unavailable, malformed output, duplicate run.
- [ ] Every shim call is appended to a call log, so tests can assert that dry-run and refusal paths make no call.
- [ ] Real-tool tests, gated by environment variables (`HEP_SLURM_TEST=1`, `HEP_HTCONDOR_TEST=1`) and skipped
  otherwise, run the B11 campaign on an approved local installation (Q1) and record versions.

**Acceptance:**

- [ ] Every normalized state of B03 is produced by at least one shim scenario and asserted in both backends where the
  backend has that state.
- [ ] The shim tests run in the default suite in under 30 s `[Proposal]`, with standard library and core requirements
  only.
- [ ] Adapter status rule: with shim tests only, the tools stay `documented`. They become
  `demonstrated-on-synthetic-data` only after the real-tool tests pass in a declared environment
  (`docs/adapter-authoring.md`).

---

### B09 (P2) — Provenance of a batch campaign

**Files:**

- `core/partition` (writer)
- new test
- optional contract change (Q4)

**Implement:**

- [ ] `campaign report` writes a `computational-run` artifact:
  - `input_manifest` with sha256;
  - `tools` with scheduler name and version (queried, never assumed);
  - `commands`: the exact submit commands;
  - `environment`: backend, config hash, container image;
  - `seeds`: from the manifest;
  - `tolerances`: the merge tolerance;
  - `exit_status`;
  - `output_hashes`: per chunk and merged;
  - `resources`: per-attempt elapsed time and peak memory where the scheduler reports them.
- [ ] Per-chunk attempts (job IDs, hosts, normalized states) go into `environment.execution` `[Proposal]`. That avoids a
  schema change; a dedicated optional field is Q4.
- [ ] An incomplete campaign produces an artifact with `failed` or `incomplete` status, never `observed` results. (r2: `incomplete` is not an
  artifact status in `contracts/vocab/core.json`; an incomplete campaign carries `failed`, a non-zero `exit_status`, and
  `environment.execution.campaign_status: "incomplete"`; §10 R2)

**Acceptance:**

- [ ] The artifact from the shim campaign passes `contracts/validate.py`.
- [ ] An artifact from a campaign with a stopped chunk carries `failed` and validates. Removing the status triggers
  `status.failed_unlabeled`.

---

### B10 (P1) — Reference: `batch-scheduling.md`

**Files:** new `skills/hep-computing/references/batch-scheduling.md`.

**Content** (every tool fact checked per Rule 4, with version and date):

- [ ] **When to batch.** Embarrassingly parallel work (event generation, histogram filling, toys for `hep-statistics`,
  systematic variations) vs work that needs a workflow system (§5).
- [ ] **Slurm and HTCondor side by side:**
  - arrays vs queue over item data;
  - shared file system vs file transfer;
  - requeue vs eviction-restart semantics;
  - accounting vs job event log;
  - held jobs;
  - exit code and signal reporting;
  - resource request syntax;
  - GPUs;
  - containers.
- [ ] **Sizing.** Pilot chunk; chunk count vs scheduler limits (array size, queue limits: site-specific, never assumed);
  throttling; memory headroom; walltime from the pilot, not from a guess.
- [ ] **The plugin's rules applied.** Seeds from the manifest; write-once outputs; duplicates never summed; bounded
  retries; held jobs need a person; site facts from config; polling etiquette; heavy work never on login nodes.
- [ ] **Consumers and handoffs.**
  - `hep-statistics` toy campaigns: the coverage-study rule "dropping failed fits can bias results" applies to dropped chunks too.
  - `physics-ml` single-node GPU training jobs. Multi-node DDP stays with `physics-ml`'s distributed-training reference (§5).
- [ ] **A worked walkthrough** reproduced by B11's output.

**Acceptance:**

- [ ] Every command line in the reference is exercised by a shim test or marked as checked against a cited version's
  documentation.
- [ ] Layering passes: no experiment names outside example blocks.

---

### B11 (P2) — Example `examples/batch-partition/`

**Files:**

- new `examples/batch-partition/run.py` and committed `output/`
- `tests/examples/test_batch_partition.py`
- `docs/maintenance.md` example table

**Implement:**

- [ ] Run T21's synthetic job through both backends using the shims. Inject one eviction duplicate, one
  out-of-memory with a recorded resource change, and one deterministic failure that stops after two attempts.
  Then `reset` with a reason, resubmit within `max_attempts`, collect, and merge.
- [ ] Write `results.json` with pass/fail per criterion, as T21 does.

**Acceptance:**

- [ ] For each backend, the merged result equals the local single-run result exactly.
- [ ] Attempts and stop reasons match the injected faults; the output is byte-reproducible across runs.
- [ ] Labeled synthetic in file names and metadata (`tasks/hep-research-plugin.md` §2.1).

---

### B12 (P2) — Privacy, credentials and blinding

**Files:**

- `tools/check_packaging.py` (extend if needed)
- `adapters/batch-schedulers/`
- tests

**Implement:**

- [ ] **Job stdout, stderr and event logs are outputs.** The campaign directory is passed to
  `skills/hep-computing/scripts/audit_blinded_outputs.py` scope in the reference and the example. The example runs
  the audit on its logs.
- [ ] **No credentials are handled.** No tokens, grid proxies or passwords are read, stored, generated or passed by the
  adapter. Authentication is the user's environment. The reference says so.
- [ ] **No site data in the plugin.** The packaging check flags scheduler configs with non-placeholder accounts, user names or
  absolute home paths under `adapters/` or `examples/`.

**Acceptance:**

- [ ] A test plants a sealed blinded value in a shim job's stdout, and the audit reports it.
- [ ] A test plants a fake account name in a copy of the example config, and `check_packaging.py` fails.

---

### B13 (P1) — Integration

**Files:**

- new `adapters/batch-schedulers/adapter.json` (`owner_skill: hep-computing`)
- `skills/hep-computing/SKILL.md`
- `tests/routing/cases.json`
- `docs/capability-matrix.md`
- `VALIDATION.md`
- `CHANGELOG.md`
- `core/OWNERS.json`
- `docs/provenance-new.csv`

**Implement:**

- [ ] `adapter.json`: tools Slurm and HTCondor, each with its own status and tested versions (empty until a real-tool
  test runs), environment, assets, tests. The adapter status is the lowest of the two.
- [ ] SKILL.md Resources: link the reference and adapter by name. Stay within 8,192 B and 180 lines. Change the
  description only if routing needs it: add "Slurm, HTCondor" within 1,024 chars.
- [ ] Add ≥ 6 routing cases (≥ 2 zh-Hant):
  - an sbatch array for toys;
  - a held HTCondor job;
  - jobs evicted and counted twice;
  - sizing memory from a pilot;
  - GPU training job submission (expected `hep-computing` with a `physics-ml` chain where the model is the subject);
  - one negative case (statistical interpretation of toy results → `hep-statistics`).
- [ ] Capability-matrix row and `VALIDATION.md` section `BATCH-RUN` with commands, environment and pass/fail/skip/unverified
  counts. CHANGELOG entry. Register new files with `tools/check_traceability.py --write-new`.

**Acceptance:**

- [ ] `tools/run_all_checks.py` passes all aggregate checks; `tools/check_relocation.py` passes.
- [ ] `tests/adapters/test_adapter_declarations.py` passes with the new adapter, and the matrix row matches
  `adapter.json`.
- [ ] `tools/check_routing_static.py` passes with the new cases; `tools/measure_entrypoints.py --no-cli` passes.
- [ ] Nothing describes Slurm or HTCondor support more strongly than the tests that ran: shim-only means `documented`.

---

## 4. Capability items (not part of this order; do only if requested)

- [ ] **C01:** Other schedulers (PBS/Torque, LSF, SGE) as further backends behind the same interface.
- [ ] **C02:** HTCondor DAGMan or Slurm job dependencies for multi-stage campaigns (generate → reconstruct → fill → merge).
- [ ] **C03:** Checkpointing of long chunks (HTCondor self-checkpointing, Slurm signal before time limit), with the
  write-once rule preserved.
- [ ] **C04:** Multi-node distributed training launch under Slurm, owned jointly with `physics-ml`.
- [ ] **C05:** HTCondor Python bindings as an alternative to the CLI, if the user's sites standardize on them.

---

## 5. Out of scope

- Grid and workflow management systems (for example CRAB, PanDA, DIRAC, Ganga), Kubernetes, cloud batch services.
- Managing credentials, proxies or tokens; site onboarding; quota negotiation.
- Submitting to, cancelling on, or otherwise acting on a user's real cluster without per-action approval (Rule 1).
- Automatic resource escalation, automatic hold release, or retries beyond the configured maximum.
- Any change to the scientific meaning of chunk results; merge semantics stay as in T21.

---

## 6. Global Definition of Done

- [ ] F1–F4 are each addressed, or recorded as changed by Phase 0 with the reason.
- [ ] T21 output is byte-identical; all existing suites and aggregate checks still pass.
- [ ] Every normalized state and failure class is covered by a shim test for each backend that has it. Every
  state-changing command defaults to dry-run.
- [ ] No tool fact remains `[To verify]` in plugin files: each is checked against a cited version's documentation or
  a real run, with the version recorded.
- [ ] Environment failures, tool skips and product defects are reported separately. Shim-only results are never
  described as real-scheduler support.

---

## 7. Sources to check before use (all `[To verify]`)

Record the version and date read for each:

- **Slurm:** `sbatch` (arrays, throttling, requeue options, parsable output), `sacct` (fields, parsable output, job state
  codes, `ExitCode` format), `squeue`, `scancel`.
- **HTCondor manual:** submit description commands (`queue` forms, `request_*`, file transfer and remaps, `max_retries`,
  `on_exit_remove`, container universe), job event log format and event codes, `JobStatus` codes, hold reasons,
  `condor_q` / `condor_history` JSON output, terse submit output.

---

## 8. Open Questions

- **Q1:** Approve a disposable local Slurm (single node, for example in a container) and/or a personal HTCondor pool for
  the real-tool tests? Which installation route is acceptable (container image, conda-forge package if available
  `[To verify]`, distribution package)? Without them both tools stay `documented`.
- **Q2:** Which scheduler versions and sites should the reference target first, so the `[To verify]` facts are checked
  against the right documentation?
- **Q3:** Accept the `[Proposal]` defaults:
  - duplicate rule: first valid by attempt order;
  - minimum poll interval: 60 s;
  - required Slurm keys: partition and time;
  - shim suite time: under 30 s.
- **Q4:** Keep per-attempt execution records inside `computational-run.environment.execution`, or add a dedicated
  optional contract field (minor contract version per `docs/maintenance.md`)?
- **Q5:** Should `watch` ever be allowed to resubmit automatically (`auto_resubmit` with `max_attempts`), or stay
  observe-and-collect only, with resubmission always an explicit command?

---

## 9. Final Report (deliver at the end)

1. **Environment:** OS, Python, core packages, scheduler versions if installed, commit hash.
2. **Phase 0 table:** F1–F4 confirmed or not; T21 checksum.
3. **Per-task summary:** files, tests (names), behavior before and after, decisions logged in `DECISIONS.md`.
4. **Test results:** per suite pass / fail / error / skip, with shim-only and real-tool results reported separately.
5. **Tool facts:** each `[To verify]` item with its source, version and date.
6. **Documentation updates:** VALIDATION, capability matrix, CHANGELOG, adapter declaration.
7. **Open items:** blocked parts (for example Q1 not approved), deferred C items, decisions needing the user.

---

## 10. Revision r2 changes (2026-10-03)

Phase 0 on `ae2b4d2`: Linux 6.18, Python 3.11.15, numpy 2.4.6, scipy 1.17.1, matplotlib 3.11.2, sympy 1.14.0 in
`.venv-hep`; 1165 unit tests OK (76 skipped: optional tools absent), `run_all_checks.py` all pass, layering clean,
entry points within budget, T21 `results.json` sha256 `fd31c56c…997b` reproduced byte for byte. No `sbatch`, `sacct`,
`squeue`, `scancel`, `condor_submit`, `condor_q`, `condor_history`, `condor_rm` on `PATH`. F1 confirmed (grep finds
the words only in the two routing cases), F2 confirmed (`run()` calls the worker in-process), F3 confirmed (a scratch
adapter importing a skill script is rejected by `check_layering.py`, rule `direction`). F4 stays inferred until the
documentation check.

| # | Change | Reason |
|---|---|---|
| R1 | Contracts are `1.1.0`, not `1.0.0`. `computational-run` did not change in 1.1.0, so B09 needs no contract change (Q4 answered: keep `environment.execution`). | PR #13 |
| R2 | An incomplete campaign is labeled `failed` with a non-zero `exit_status`; `incomplete` is recorded in `environment.execution.campaign_status`, not as an artifact status. | `artifact_statuses` has no `incomplete` |
| R3 | The new per-chunk attempt list is `attempt_records`; the existing integer `attempts` keeps its meaning. State files without `attempt_records` read as an empty list. | name clash in `state.json` |
| R4 | Backend modules are `slurm_backend.py` and `htcondor_backend.py`; the campaign CLI is `adapters/batch-schedulers/batch_campaign.py`. The CLI lives in the adapter because the provenance writer needs `contracts/`, which `core/` may not import. | Python package `htcondor` (bindings) would be shadowed; layering |
| R5 | Write-once on a shared file system is enforced by the runner: the final output is created with a no-clobber link; a second execution of the same attempt (eviction, requeue) writes `<attempt>.rerun-<k>.json`, which collection records as a duplicate. The duplicate rule is "first valid by attempt order at collection time; once a chunk is ingested its output never changes". | duplicates must never be summed (B02) |
| R6 | Job stdout and stderr are named `*.stdout.log` / `*.stderr.log`; in execution `core/blinding` also learned to read `.out`, `.err`, `.sh`, `.sbatch` and `.sub` as text, because a campaign audit was otherwise `incomplete` (job descriptions were unscanned). | B12 |
| R7 | `tools/check_packaging.py` gains `--root` so the B12 test can scan a planted copy. | B12 acceptance |
| R8 | Shim fault injection is keyed by chunk ID: the shim reads the submission map named in the generated job description. | readable tests |
| R9 | Q1: the user chose no real Slurm or HTCondor installation (2026-10-03, "不用，只用模擬排程器測試"); shim tests only, both tools stay `documented`, and the real-tool parts of B04, B05 and B08 are not done by user choice (the gated tests skip). Q2: current upstream documentation, version and date recorded per fact; the documentation check needs the user to approve the URLs. Q3: `[Proposal]` defaults accepted. Q4: `environment.execution`. Q5: `watch` observes and collects only; resubmission is always an explicit command (`auto_resubmit` is not implemented). C01–C05 not done. | user (Q1), coordinator defaults |
| R10 | `monitor.deadline_s` (seconds from the start of `watch`) replaces the absolute `deadline`, so tests and reruns are deterministic. | B06 |
| R11 | Routing cases are added to `tests/routing/make_cases.py` (cases.json is generated); the adapter CLI is named in SKILL.md by its `${CLAUDE_PLUGIN_ROOT}` path. | existing tests |
