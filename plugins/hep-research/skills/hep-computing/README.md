# hep-computing

Working, reproducible scientific software and its execution, with each durable run recorded as a `computational-run` artifact.

## Core capabilities

- Writing, debugging and reviewing physics code: Python, C++, ROOT and PyROOT, uproot and awkward, RDataFrame.
- Crashes and memory leaks, CMake builds, data I/O and formats, performance.
- Symbolic and numerical computation.
- Environment and run manifests; experiment software environments.
- Partitioning, batch submission, merging and recovery.
- Advisory blinding checks of outputs, logs and caches.
- Authoring an implementation-ready research task.
- Owns: scientific software, symbolic and numerical execution, builds, I/O, debugging, performance, manifests, partition/merge/recovery, reproducibility, advisory blinding checks (enforcement lies outside the agent), research-task authoring; stewardship of `core/blinding` and `core/partition`.
- Typical artifacts: code, `computational-run`, output audits.

## Triggering conditions

Use when:

- The deliverable is working, reproducible scientific software or its execution.
- Code is to be written, debugged, reviewed, built, profiled or run, including small, verified code changes.
- A run needs an environment or run manifest, partitioning, batch submission, merging or recovery.
- Outputs, logs or caches need an advisory blinding check.
- A research task is to be written for a coding agent.

Not for deciding the physics or statistics:

| Need | Hand to |
|---|---|
| Physics meaning of a numerical result | hep-theory or hep-measurement |
| Statistical interpretation | hep-statistics |
| Model training issues | hep-ml |
| Reports, figures, write-ups | hep-authoring |

## Workspace directory architecture

```text
hep-computing/
├── SKILL.md
├── README.md
├── references/
├── scripts/
├── assets/
│   └── workflow/
└── examples/
```

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | thirty-seven references: engineering playbook, agile delivery, task authoring, ROOT design and debugging, crash and memory debugging, performance profiling, symbolic and numerical computation, CMake, Python HEP patterns, analysis data pipelines, storage, environments and containers, batch scheduling, numerical methods, design guidelines (Python, C++, Bash), validation and definition of done, ROOT usage patterns, the preservation checklist, columnar and large-scale data, analysis workflows, research workflow control (evidence tiers, task record, completion report), the semantic naming charter |
| `scripts/` | nineteen helpers: interpreter choice, ROOT inspection and comparison, histogram error checks, environment manifests, synthetic NanoAOD, task and skill-bundle validation, local partition, a workflow runner, blinding audits, the naming extractor (code, files, ROOT objects, columns, configuration, jobs, plugin vocabulary) |
| `assets/` | task template, story card, definition of done, completion summary, risk register, example configs, the time-slice reduction helper, a chunked-histogram template, an example workflow (`workflow/`: workflow.json and a Snakefile) |
| `examples/` | worked research tasks (bug, research, migration, agentic loop, data/ML, physics code) with their own README |

## Input and output specifications

Inputs:

- Request: code to write, fix, review, build or run; a run to define, partition or recover; a task to author.
- Profiles and context: read only through the context-resolution steps in `SKILL.md`; experiment modules only for the data formats or conventions the code needs. No experiment facts are embedded in the skill.
- Files and artifacts read: source code, ROOT files, JSON histogram bundles, workflow and partition configs, task Markdown, run outputs, logs and caches.

Outputs:

- Code and output audits.
- `computational-run` artifacts for durable results, written as JSON into the project's `artifacts_dir`, never inside the plugin.

### Scripts

- `find_python.py` picks the interpreter for package-dependent work (Python 3.13 or newer only; a `--min-python` below 3.13 is bad usage, exit 2).
- `inspect_root_file.py` and `roofit_workspace_summary.py` inspect ROOT files with PyROOT (exit 3 without it).
- `summarize_histogram_statistics.py` summarizes a histogram with PyROOT or, for 1D histograms, uproot through the reader of `check_histogram_errors.py` (both give the same summary; exit 3 without either).
- `check_histogram_errors.py` checks error bookkeeping (Sum of w^2 for weighted fills, stored errors consistent with the fill, negative bins, flow fraction, TEfficiency passed <= total) with PyROOT or uproot, or on a canonical JSON form.
- `compare_root_histograms.py` compares histograms with PyROOT or, without it, uproot.
- `audit_histograms.py` checks a JSON histogram bundle and needs neither.
- `check_root_cpp_env.sh` and `new_root_cpp_project.sh` set up C++ work.
- `environment_manifest.py` records and checks a run's environment.
- `make_synthetic_nanoaod.py` writes a synthetic NanoAOD file.
- `lint_task.py`, `validate_agile_notes.py` and `create_story_card.py` support task authoring (the example-authoring tools and the bundle check are maintenance tools in `<plugin root>/tools/`).
- `local_partition.py` partitions work with bounded resubmission and a duplicate-safe merge (engine in `core/partition`).
- `assets/time_slice_reduction.py` deduplicates time-sliced records by a stable key and then sums them, alone or as a `local_partition.py` worker with a `finalize` step that records the merge inputs (C1).
- `run_workflow.py` runs a workflow DAG (`assets/workflow/workflow.json`, mirrored by a Snakefile) with a computational-run per step, byte-identical on a rerun (C6).
- `audit_blinded_outputs.py` scans outputs for synthetic blinding sentinels (with real data, sealing and scanning belong to the data custodian).
- Batch campaigns on Slurm and HTCondor use `adapters/batch-schedulers/batch_campaign.py`, tested only against fake schedulers.
- The optional `adapters/cr-propagation` (owned here) runs DRAGON2 from a JSON run spec and records the run (`dragon2_run.py`), and turns each run into one grid-node `prediction` for the comparison gate and `covariance_fit.py` model `tabulated-grid` (`dragon2_to_prediction.py`). DRAGON2 is `tested-in-declared-environment` (commit cd588707, built on E2), GALPROP and USINE `proposed`, so the adapter is `proposed`; a run that terminates is not a validated prediction.

### Script contract

`SKILL.md` invariant 5: JSON with a `status` key, exit 0 success, 1 negative verdict, 2 bad input, 3 missing optional dependency or incomplete, no traceback on bad input or an unwritable output, files located from the script's own path. State after the 2026-10 remediation (CMP-08); checked by `tests/skills/test_cli_robustness.py`.

| Script | JSON `status` | Output option | Exits | Missing dependency | Category |
|---|---|---|---|---|---|
| `audit_blinded_outputs.py` | always | seal `--out`, scan `--report` (refused cleanly) | 0/1/2/3 | numpy only for caches | user |
| `audit_histograms.py` | always | none | 0/1/2 | none | user |
| `check_root_cpp_env.sh` | `--json` | private temporary folder | 0/1/2/3 | root, root-config: exit 3 | user |
| `check_histogram_errors.py` | always | none | 0/1/2/3 | PyROOT or uproot (ROOT files only): exit 3 | user |
| `compare_root_histograms.py` | always | none | 0/1/2/3 | PyROOT or uproot: exit 3 | user |
| `environment_manifest.py` | always | `--out` (folders created) | 0/1/2/3 (`pairs`: 1 a data/MC version mismatch, 3 an undeclared version) | none | user |
| `find_python.py` | always | none | 0/1/2 | reports candidates | user |
| `inspect_root_file.C` | exempt (ROOT macro) | none | ROOT's | runs inside ROOT | user |
| `inspect_root_file.py` | `--json` | none | 0/2/3 | PyROOT: exit 3 | user |
| `lint_task.py` | `--json` | none | 0/1/2 | none | user |
| `local_partition.py` | always | plan `--out`, `--state` (folders created) | 0/1/2 | none | user |
| `make_synthetic_nanoaod.py` | always | `--out` (folders created) | 0/2/3 | numpy, awkward, uproot: exit 3 | user |
| `new_root_cpp_project.sh` | `--json` | `--dir` (refuses a non-empty target) | 0/2 | none | user |
| `roofit_workspace_summary.py` | `--json` | none | 0/2/3 | PyROOT: exit 3 | user |
| `summarize_histogram_statistics.py` | `--json` | none | 0/2/3 | PyROOT: exit 3 | user |
| `create_story_card.py` | `--json` | `--output` (folders created) | 0/2 | none | maintenance |
| `validate_agile_notes.py` | `--json` | none | 0/1/2 | none | maintenance |

## Setup requirements

- Python 3.13 or newer; scripts are standard library first and take `--help`.
- Optional packages, per script (see the script contract): PyROOT, uproot, awkward, numpy; a ROOT installation (`root`, `root-config`) for the C++ helpers and `inspect_root_file.C`.
- Environment variable `HEP_RESEARCH_PYTHON`: an interpreter `find_python.py` tries after `--python` and before the calling interpreter and `python3` on PATH.
- No system-wide installs or network fetches without the user's approval and within the session's egress policy.

### Python floors

Three tiers (C4):

- The plugin's Python scripts, `core/` and `contracts/` need Python 3.13 or newer; `find_python.py` picks such an interpreter and refuses an older one.
- ROOT interoperability may run lower: the `inspect_root_file.C` macro and the C++ project templates run under ROOT's own interpreter and compiler, and a PyROOT built for an older Python may inspect a file, but its results are not recorded as test evidence (`test_pyroot_floor.py`).
- Environment probes (`check_root_cpp_env.sh`) only report what they find and state the versions they saw.

## Operational constraints

- Never treats a successful run as scientific validity.
- Never installs software system-wide or fetches from the network without the user's approval or beyond the session's egress policy.
- Blinding checks are advisory; enforcement lies outside the agent. `audit_blinded_outputs.py` works on synthetic sentinels only; with real data, sealing and scanning belong to the data custodian.
- Batch submission is unsandboxed execution: synthetic test environments only, each submission user-approved.
- Reproducibility: record input checksums, tool and library versions, exact commands, seeds, tolerances and environment; partitioned work uses a manifest with duplicate-safe merges.
- `SKILL.md` is the authoritative statement of ownership, invariants and workflow; it is the entry point the host loads (its front matter carries the description that routes a request here; it stays under 8 KiB). This README is for people browsing the folder.

Entry references: `references/engineering-playbook.md` and `references/validation-and-done.md` set the working discipline; `references/task-authoring-guide.md` with `assets/task-template.md` is the entry point for writing a task for a coding agent; `references/batch-scheduling.md` for campaigns; `references/environments-and-containers.md` for LCG views and containers; `references/crash-and-memory-debugging.md`, `references/performance-profiling.md` and `references/symbolic-and-numerical-computation.md` for crashes and leaks, speed, and SymPy/SciPy accuracy.

## Validation

- `tests/skills/hep_computing/` (twenty-one test modules, including `test_pyroot_floor.py`: a PyROOT interpreter older than Python 3.13 is not used as ROOT evidence).
- The `core/partition` and `core/blinding` tests under `tests/core/`.
- The `local-partition` and `batch-partition` examples under `examples/`.
- `tests/skills/test_cli_robustness.py` runs every shipped script with a missing input and checks the JSON status and exit codes of this skill's scripts (the script contract above).
- What is and is not validated: `docs/capability-matrix.md`; the evidence: `VALIDATION.md`.

## Example requests

Routing examples from `SKILL.md`:

<!-- example -->
- "Memory leak in my AMS-02 ntuple script" (the AMS profile is read only if the data format matters).
- "Build or run my analysis code against an experiment's software framework (setup script, compiler, framework program)" (plus the bound experiment profile's software modules when it has them).
<!-- /example -->
