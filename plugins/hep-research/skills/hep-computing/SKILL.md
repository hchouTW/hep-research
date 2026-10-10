---
name: hep-computing
description: "Use when the deliverable is working, reproducible scientific software or its execution: writing, debugging and reviewing physics code (Python, C++, ROOT/PyROOT, uproot/awkward, RDataFrame), crashes and memory leaks, CMake builds, data I/O and formats, performance, symbolic and numerical computation (SymPy, integration, ODEs, convergence and tolerance studies), environment and run manifests, partitioning, batch submission, merging and recovery (Slurm and HTCondor job arrays, held or evicted jobs, pilot sizing), advisory blinding checks of outputs, logs and caches, experiment software environments and build chains, and authoring an implementation-ready research task. Also small, verified, reviewable code changes. Applies even when the code belongs to a named experiment. Not for deciding the physics or statistics: hep-analysis, detector-response, hep-theory (derivations), hep-statistics (inference), physics-ml."
---

# hep-computing: scientific software and execution

**Owns:** scientific software, symbolic and numerical execution, builds, I/O, debugging, performance, manifests, partition/merge/recovery, reproducibility, advisory blinding checks of outputs, logs and caches (enforcement lies outside the agent), research-task authoring; stewardship of `core/blinding`.
**Typical artifacts:** code, `computational-run` (inputs with checksums, tool versions, commands, environment, seeds, tolerances, exit status, output hashes), output audits.
**Never:** treat a successful run as scientific validity; install software system-wide or fetch from the network without the user's approval or beyond the session's egress policy (queries never carry protected content).

## Invariants

- Execution success is not scientific validity; a run that terminates has not necessarily converged. Report tolerances and refinement studies.
- Record what is needed to reproduce: input checksums, tool and library versions, exact commands, seeds, tolerances, environment.
- Partitioned work uses a manifest: no duplicate events or chunks on resubmission, missing work detected, merged and single-run results agree within a declared tolerance. Automatic retries only with a configured maximum attempt count; absent config means no retries; repeated identical failures stop with state retained.
- Blinded values never appear in plots, logs, caches, or reports produced by the code.
- Scripts locate their files from their own path, take an explicit output directory, emit an exit code plus a JSON status, and explain missing optional dependencies.
- Changes are small and verifiable: state acceptance criteria and how they were checked; keep diffs surgical.
- Failures (missing tools or licenses, nonconvergence, invalid outputs) are explicit statuses passed downstream.

## Workflow

1. Resolve context (stanza below); load experiment modules only for data formats or conventions the code needs.
2. Reproduce the problem or define the run; capture the environment.
3. Make the smallest change that fixes or implements it; add or run a test.
4. Record the `computational-run` artifact for durable results.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

`<plugin root>` is the folder two levels above this `SKILL.md`.

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; read a bound profile before answering about its experiment. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; check them with `python3 "<plugin root>/contracts/project.py" <project-dir>`. A bound profile in neither place, or at a local path known to be a companion's, is used only via the installed `<plugin>:profile` skill that names it, after its preflight, from its folder; never scan for companions. If none is installed, the preflight fails, or a non-public profile lacks `agent_policy` approval for this host (none has it yet), say it is unavailable, do other work; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never in the plugin; check them with `python3 "<plugin root>/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English.
<!-- END context-resolution -->

## Resources

Guides under `references/`: [engineering playbook](references/engineering-playbook.md) and [agile delivery](references/agile-development-guide.md); [research task authoring](references/task-authoring-guide.md) with `assets/task-template.md` and worked tasks in `examples/`; [ROOT design](references/root-balanced-design-guidelines.md), [CMake](references/cmake-and-build.md), [ROOT debugging](references/root-debugging.md), [Python HEP coding](references/python-hep-coding-patterns.md) and [CERN EOS](references/storage-cern-eos.md); [numerical and computational methods](references/numerical-and-computational-methods.md); design guidelines: [Python](references/python-balanced-design-guidelines.md), [C++](references/cpp-balanced-design-guidelines.md), [Bash](references/bash-balanced-design-guidelines.md); [validation and definition of done](references/validation-and-done.md).

Scripts in `<plugin root>/skills/hep-computing/scripts/` (read `--help` first): interpreter choice for package-dependent work (SymPy) (`find_python.py`: `--python`, then `HEP_RESEARCH_PYTHON`, the caller, `python3` on PATH), ROOT file inspection and comparison (`inspect_root_file.py`, `compare_root_histograms.py`, `summarize_histogram_statistics.py`, `roofit_workspace_summary.py`, `audit_histograms.py`), environment and project checks (`check_root_cpp_env.sh`, `new_root_cpp_project.sh`, `environment_manifest.py` to record and check a run's environment; LCG views and containers: [environments](references/environments-and-containers.md)), `make_synthetic_nanoaod.py`, task checks (`lint_task.py`), local partition with bounded resubmission and duplicate-safe merge (`local_partition.py`; engine in `core/partition`), and advisory blinding checks (`audit_blinded_outputs.py`, `core.blinding.check_figure`): synthetic sentinels only; with real data, sealing and scanning belong to the data custodian. ROOT/uproot starting points: `<plugin root>/adapters/root-uproot/assets/`. Slurm and HTCondor campaigns: [batch scheduling](references/batch-scheduling.md) and the optional campaign CLI `<plugin root>/adapters/batch-schedulers/batch_campaign.py` (documented; tested only against fake schedulers). Submission is unsandboxed execution: synthetic test environments only, each submission user-approved.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Physics meaning of a numerical result | hep-theory / hep-analysis | `computational-run` |
| Statistical interpretation | hep-statistics | `computational-run` |
| Model training issues | physics-ml | `ml-artifact` |
| Reports, figures, write-ups | research-communication | `computational-run` |

<!-- example: routing -->
- "Memory leak in my AMS-02 ntuple script" → this skill; the AMS profile is read only if the data format matters.
- "Build or run my analysis code against an experiment's software framework (setup script, compiler, framework program)" → this skill, plus the bound experiment profile's software modules when it has them.
<!-- /example -->
