# hep-computing

Use when the deliverable is working, reproducible scientific software or its execution: writing, debugging and reviewing physics code (Python, C++, ROOT and PyROOT, uproot and awkward, RDataFrame), crashes and memory leaks, CMake builds, data I/O and formats, performance, symbolic and numerical computation, environment and run manifests, partitioning, batch submission, merging and recovery, advisory blinding checks of outputs, logs and caches, experiment software environments, and authoring an implementation-ready research task.

**Owns:** scientific software, symbolic and numerical execution, builds, I/O, debugging, performance, manifests, partition/merge/recovery, reproducibility, advisory blinding checks (enforcement lies outside the agent), research-task authoring; stewardship of `core/blinding` and `core/partition`. Typical artifacts: code, `computational-run`, output audits.

**Never:** treat a successful run as scientific validity; install software system-wide or fetch from the network without the user's approval or beyond the session's egress policy.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | twenty-nine references: engineering playbook, agile delivery, task authoring, ROOT design and debugging, CMake, Python HEP patterns, storage, environments and containers, batch scheduling, numerical methods, design guidelines (Python, C++, Bash), validation and definition of done |
| `scripts/` | twenty helpers: interpreter choice, ROOT inspection and comparison, environment manifests, synthetic NanoAOD, task and skill-bundle validation, local partition, blinding audits |
| `assets/` | task template, story card, definition of done, completion summary, risk register, example configs |
| `examples/` | worked research tasks (bug, migration, data/ML, agentic loop) with their own README |

## Scripts

`find_python.py` picks the interpreter for package-dependent work; `inspect_root_file.py`, `compare_root_histograms.py`, `summarize_histogram_statistics.py`, `roofit_workspace_summary.py` and `audit_histograms.py` inspect ROOT files (PyROOT or uproot when installed, skipped otherwise); `check_root_cpp_env.sh` and `new_root_cpp_project.sh` set up C++ work; `environment_manifest.py` records and checks a run's environment; `make_synthetic_nanoaod.py`; `lint_task.py`, `validate_skill_bundle.py`, `validate_skill_example.py`, `validate_agile_notes.py`, `create_story_card.py`, `generate_skill_example.py` and `check_example_diversity.py` support task authoring; `local_partition.py` partitions work with bounded resubmission and a duplicate-safe merge (engine in `core/partition`); `audit_blinded_outputs.py` scans outputs for synthetic blinding sentinels (with real data, sealing and scanning belong to the data custodian). Batch campaigns on Slurm and HTCondor use `adapters/batch-schedulers/batch_campaign.py`, tested only against fake schedulers.

## References

`references/engineering-playbook.md` and `references/validation-and-done.md` set the working discipline; `references/task-authoring-guide.md` with `assets/task-template.md` is the entry point for writing a task for a coding agent; `references/batch-scheduling.md` for campaigns; `references/environments-and-containers.md` for LCG views and containers.

## Handoffs

| Need | Hand to |
|---|---|
| Physics meaning of a numerical result | hep-theory or hep-analysis |
| Statistical interpretation | hep-statistics |
| Model training issues | physics-ml |
| Reports, figures, write-ups | research-communication |

## Tests and validation

`tests/skills/hep_computing/` (eleven modules), the `core/partition` and `core/blinding` tests under `tests/core/`, the `local-partition` and `batch-partition` examples under `examples/`, and `tests/skills/test_cli_robustness.py`, which runs every shipped script with a missing input. What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
