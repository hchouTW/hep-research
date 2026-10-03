# Final Report: Slurm and HTCondor batch execution (work order B01–B13, r2)

Date 2026-10-03. Branch `claude/batch-schedulers-llt7jk` from `main` at `ae2b4d2`; evidence at `6ad6228` and later
documentation commits. Details: VALIDATION.md section BATCH-RUN; decisions BATCH-01..09 in `DECISIONS.md`.

## 1. Environment

Claude Code cloud container, Linux 6.18 x86_64, Python 3.11.15; `.venv-hep` with numpy 2.4.6, scipy 1.17.1,
matplotlib 3.11.2, sympy 1.14.0. No Slurm or HTCondor installed or on `PATH` (Q1: the user chose fake schedulers
only). pyhf, PyTorch, ROOT, uproot/awkward, Combine and diagram tools were not installed here; their tests skip.

## 2. Phase 0 (on `ae2b4d2`)

| Item | Result |
|---|---|
| Unit tests | 1165 run, 0 failures, 76 skipped |
| `run_all_checks.py` | all pass except `ams_ledger_preservation` (skip: no legacy checkout) |
| Layering, entry points | pass |
| T21 checksum | `fd31c56c94f35800484f819e85ee7a2e8ef8dae76d606026075da25f2819997b`, fresh run identical |
| Scheduler commands on PATH | none |
| F1 (no Slurm/HTCondor content) | confirmed: the words appear only in two routing cases |
| F2 (synchronous in-process engine) | confirmed: `run()` calls the worker in-process |
| F3 (layering forbids adapter → skill import) | confirmed: a scratch adapter importing a skill script fails `check_layering.py` (rule `direction`) |
| F4 (schedulers retry on their own) | addressed by design (`--no-requeue`, no `max_retries`, restarts counted as attempts); the tool behavior itself is not checked (no documentation access, no real tool) |
| Premise changes | contracts are 1.1.0 (no `computational-run` change); no `incomplete` artifact status; `attempts` already an integer in state; `htcondor` module name would shadow the bindings package: see TASK §10 R1–R11 |

## 3. Per-task summary

| Task | Files | Tests | Before → after |
|---|---|---|---|
| B01 | `core/partition/{engine,executors,campaign}.py`; `local_partition.py` now a CLI over the engine; `core/OWNERS.json` | `tests/core/test_partition.py` | engine only in a skill script → shared core module with an executor interface and a local executor; T21 unchanged |
| B02 | `core/partition/runner.py`, collection in `campaign.py` | `test_partition_remote.py` | no remote protocol → runner with map-based chunk lookup, no-clobber outputs, validated collection, duplicates recorded, quarantine |
| B03 | `core/partition/states.py`, `campaign.py` | `test_partition_states.py` | → 13 normalized states, retry classes, signatures without host/time, explicit resubmit within `max_attempts`, resets keep history (BATCH-03) |
| B04 | `adapters/batch-schedulers/slurm_backend.py`, `assets/slurm-array.sbatch.template`, `batch_campaign.py` | `test_batch_slurm.py`, golden `slurm-array-10x3.sbatch` | → array per submission, `--no-requeue`, sacct with `--duplicates`, squeue + runner fallback |
| B05 | `htcondor_backend.py`, `assets/htcondor-chunks.sub.template` | `test_batch_htcondor.py`, golden `htcondor-chunks-transfer.sub` | → item-data queue, event log, condor_q/history confirmation, held never released |
| B06 | `campaign.watch`, CLI `status`/`watch` | `test_batch_watch.py` | → one-poll status; watch with interval ≥ 60 s and max_polls/deadline, early stops |
| B07 | `batch_config.py`, `assets/batch-config.example.json` | `test_batch_config.py` | → named refusals, unknown keys rejected, placeholders only with `--example` |
| B08 | `tests/adapters/batch_shims/`, `batch_harness.py` | all shim tests | → fake schedulers with fault injection and a call log; real-tool tests gated and skipped |
| B09 | `batch_campaign.py report` | `test_batch_provenance.py` | → `computational-run` with attempts in `environment.execution`; incomplete = `failed` |
| B10 | `skills/hep-computing/references/batch-scheduling.md` | `test_batch_reference.py` | → reference with workflow, side-by-side table, sizing, rules, walkthrough, tool-facts table |
| B11 | `examples/batch-partition/` | `tests/examples/test_batch_partition.py` | → T21 job on both fake schedulers, 10 criteria each, exact merge equality, byte-reproducible |
| B12 | `core/blinding` text suffixes, `tools/check_packaging.py` | `test_batch_privacy.py` | job descriptions were unscanned → read as text; site facts in shipped configs flagged |
| B13 | `adapter.json`, SKILL.md, routing table, matrix, README, adapter guide, CHANGELOG, VALIDATION, provenance rows | declaration, routing, resource tests | → adapter `documented`, 6 routing cases |

## 4. Test results

| Suite | Run | Pass | Fail | Skip |
|---|---|---|---|---|
| Full unit suite (final) | 1240 | 1162 | 0 | 78 (76 as at Phase 0, 2 real-scheduler) |
| Fake-scheduler and core/partition tests (subset) | 74 | 72 | 0 | 2 (real Slurm, real HTCondor) |
| Profile suites | 258 / 9 / 16 | all | 0 | 0 |
| Aggregate checks | 14 | 13 | 0 | 1 (`ams_ledger_preservation`) |
| Relocation | 14 | 12 | 0 | 2 |
| Real-tool tests | 0 run | – | – | not done by user choice (Q1) |

Shim-only results are internal consistency, never real-scheduler support. No environment failures; no product
defect left open.

## 5. Tool facts

Not checked. The Slurm and HTCondor documentation pages could not be read (each WebFetch permission request timed
out unanswered), and no real tool ran. Every fact the backends use is listed with the page to check in the
reference's "Tool facts" table, marked not checked. This is the main open item (Global DoD item 4 not met).

## 6. Documentation updates

VALIDATION BATCH-RUN; capability matrix (capability row and `adapters/batch-schedulers` row, both `documented`);
CHANGELOG "Unreleased (Slurm and HTCondor batch execution)"; `adapters/batch-schedulers/adapter.json` (Slurm and
HTCondor `documented`, `tested_versions` empty); `docs/adapter-authoring.md`; README optional tools;
`docs/maintenance.md` example table; DECISIONS BATCH-01..09; TASK r2 §10.

## 7. Open items

- Tool facts unchecked: needs the documentation URLs approved (or a real run); then update the reference table and
  fix any mismatch in the backends and shims.
- Real-tool tests (B04/B05/B08 real parts): not done by user choice; both tools stay `documented`.
- No live routing run for the six new cases (paid, not approved).
- C01–C05 not done. `auto_resubmit` (Q5) not implemented by default decision.
