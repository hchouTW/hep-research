# hep-computing

Use when the deliverable is working, reproducible scientific software or its execution: writing, debugging and reviewing physics code (Python, C++, ROOT and PyROOT, uproot and awkward, RDataFrame), crashes and memory leaks, CMake builds, data I/O and formats, performance, symbolic and numerical computation, environment and run manifests, partitioning, batch submission, merging and recovery, advisory blinding checks of outputs, logs and caches, experiment software environments, and authoring an implementation-ready research task.

**Owns:** scientific software, symbolic and numerical execution, builds, I/O, debugging, performance, manifests, partition/merge/recovery, reproducibility, advisory blinding checks (enforcement lies outside the agent), research-task authoring; stewardship of `core/blinding` and `core/partition`. Typical artifacts: code, `computational-run`, output audits.

**Never:** treat a successful run as scientific validity; install software system-wide or fetch from the network without the user's approval or beyond the session's egress policy.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | thirty-two references: engineering playbook, agile delivery, task authoring, ROOT design and debugging, crash and memory debugging, performance profiling, symbolic and numerical computation, CMake, Python HEP patterns, analysis data pipelines, storage, environments and containers, batch scheduling, numerical methods, design guidelines (Python, C++, Bash), validation and definition of done |
| `scripts/` | twenty helpers: interpreter choice, ROOT inspection and comparison, environment manifests, synthetic NanoAOD, task and skill-bundle validation, local partition, blinding audits |
| `assets/` | task template, story card, definition of done, completion summary, risk register, example configs |
| `examples/` | worked research tasks (bug, research, migration, agentic loop, data/ML, physics code) with their own README |

## Scripts

`find_python.py` picks the interpreter for package-dependent work (Python 3.13 or newer only; a `--min-python` below 3.13 is bad usage, exit 2); `inspect_root_file.py`, `compare_root_histograms.py`, `summarize_histogram_statistics.py`, `roofit_workspace_summary.py` and `audit_histograms.py` inspect ROOT files (PyROOT or uproot when installed, skipped otherwise); `check_root_cpp_env.sh` and `new_root_cpp_project.sh` set up C++ work; `environment_manifest.py` records and checks a run's environment; `make_synthetic_nanoaod.py`; `lint_task.py`, `validate_skill_bundle.py`, `validate_skill_example.py`, `validate_agile_notes.py`, `create_story_card.py`, `generate_skill_example.py` and `check_example_diversity.py` support task authoring; `local_partition.py` partitions work with bounded resubmission and a duplicate-safe merge (engine in `core/partition`); `audit_blinded_outputs.py` scans outputs for synthetic blinding sentinels (with real data, sealing and scanning belong to the data custodian). Batch campaigns on Slurm and HTCondor use `adapters/batch-schedulers/batch_campaign.py`, tested only against fake schedulers. The optional `adapters/cr-propagation` (owned here) runs DRAGON2 from a JSON run spec and records the run (`dragon2_run.py`), and turns each run into one grid-node `prediction` for the comparison gate and `covariance_fit.py` model `tabulated-grid` (`dragon2_to_prediction.py`); DRAGON2 is `tested-in-declared-environment` (commit cd588707, built on E2), GALPROP and USINE `proposed`, so the adapter is `proposed`; a run that terminates is not a validated prediction.

## Script contract

`SKILL.md` invariant 5: JSON with a `status` key, exit 0 success, 1 negative verdict, 2 bad input, 3 missing optional
dependency or incomplete, no traceback on bad input or an unwritable output, files located from the script's own path.
State after the 2026-10 remediation (CMP-08); checked by `tests/skills/test_cli_robustness.py`.

| Script | JSON `status` | Output option | Exits | Missing dependency | Category |
|---|---|---|---|---|---|
| `audit_blinded_outputs.py` | always | seal `--out`, scan `--report` (refused cleanly) | 0/1/2/3 | numpy only for caches | user |
| `audit_histograms.py` | always | none | 0/1/2 | none | user |
| `check_root_cpp_env.sh` | `--json` | private temporary folder | 0/1/2/3 | root, root-config: exit 3 | user |
| `compare_root_histograms.py` | always | none | 0/1/2/3 | PyROOT or uproot: exit 3 | user |
| `environment_manifest.py` | always | `--out` (folders created) | 0/1/2 | none | user |
| `find_python.py` | always | none | 0/1/2 | reports candidates | user |
| `inspect_root_file.C` | exempt (ROOT macro) | none | ROOT's | runs inside ROOT | user |
| `inspect_root_file.py` | `--json` | none | 0/2/3 | PyROOT: exit 3 | user |
| `lint_task.py` | `--json` | none | 0/1/2 | none | user |
| `local_partition.py` | always | plan `--out`, `--state` (folders created) | 0/1/2 | none | user |
| `make_synthetic_nanoaod.py` | always | `--out` (folders created) | 0/2/3 | numpy, awkward, uproot: exit 3 | user |
| `new_root_cpp_project.sh` | `--json` | `--dir` (refuses a non-empty target) | 0/2 | none | user |
| `roofit_workspace_summary.py` | `--json` | none | 0/2/3 | PyROOT: exit 3 | user |
| `summarize_histogram_statistics.py` | `--json` | none | 0/2/3 | PyROOT: exit 3 | user |
| `check_example_diversity.py` | `--json` | none | 0/1/2 | none | maintenance |
| `create_story_card.py` | `--json` | `--output` (folders created) | 0/2 | none | maintenance |
| `generate_skill_example.py` | `--json` | `--output` (folders created) | 0/2 | none | maintenance |
| `validate_agile_notes.py` | `--json` | none | 0/1/2 | none | maintenance |
| `validate_skill_bundle.py` | `--json` | none | 0/1 | none | maintenance |
| `validate_skill_example.py` | `--json` | none | 0/1/2 | none | maintenance |

## References

`references/engineering-playbook.md` and `references/validation-and-done.md` set the working discipline; `references/task-authoring-guide.md` with `assets/task-template.md` is the entry point for writing a task for a coding agent; `references/batch-scheduling.md` for campaigns; `references/environments-and-containers.md` for LCG views and containers; `references/crash-and-memory-debugging.md`, `references/performance-profiling.md` and `references/symbolic-and-numerical-computation.md` for crashes and leaks, speed, and SymPy/SciPy accuracy.

## Handoffs

| Need | Hand to |
|---|---|
| Physics meaning of a numerical result | hep-theory or hep-measurement |
| Statistical interpretation | hep-statistics |
| Model training issues | hep-ml |
| Reports, figures, write-ups | hep-communication |

## Tests and validation

`tests/skills/hep_computing/` (thirteen test modules, including `test_pyroot_floor.py`: a PyROOT interpreter older than Python 3.13 is not used as ROOT evidence), the `core/partition` and `core/blinding` tests under `tests/core/`, the `local-partition` and `batch-partition` examples under `examples/`, and `tests/skills/test_cli_robustness.py`, which runs every shipped script with a missing input and checks the JSON status and exit codes of this skill's scripts (the script contract above). What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
