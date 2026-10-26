---
name: hep-computing
description: "Use when the deliverable is working, reproducible scientific software or its execution: writing, debugging and reviewing physics code (Python, C++, ROOT/PyROOT, uproot/awkward, RDataFrame, RNTuple), crashes and memory leaks, CMake builds, data I/O and formats, histogram and TEfficiency objects, performance, symbolic and numerical computation (SymPy, integration, ODEs, convergence and tolerance studies), environment and run manifests, partitioning, batch submission, merging and recovery (Slurm and HTCondor job arrays, held or evicted jobs, pilot sizing), advisory blinding checks of outputs, logs and caches, experiment software environments, build chains, and authoring an implementation-ready research task. Also small, verified code changes; load it first even for a quick build or code fix. Applies even when the code belongs to a named experiment. Not for deciding the physics or statistics: hep-measurement, hep-detector (backtracing), hep-theory (derivations, table import), hep-statistics (inference), hep-ml."
---

# hep-computing: scientific software and execution

**Owns:** scientific software, symbolic and numerical execution, builds, I/O, debugging, performance, manifests, partition/merge/recovery, reproducibility, advisory blinding checks of outputs, logs and caches (enforcement lies outside the agent), research-task authoring, semantic naming of identifiers, files and named objects (charter and engine); stewardship of `core/blinding`, `core/partition` and `core/naming`.
**Typical artifacts:** code, `computational-run` (inputs with checksums, tool versions, commands, environment, seeds, tolerances, exit status, output hashes), output audits.
**Never:** treat a successful run as scientific validity; install software system-wide or fetch from the network without the user's approval or beyond the session's egress policy (queries never carry protected content).

## Invariants

- Execution success is not scientific validity; a run that terminates has not necessarily converged. Report tolerances and refinement studies.
- Record what is needed to reproduce: input checksums, tool and library versions, exact commands, seeds, tolerances, environment.
- Partitioned work uses a manifest: no duplicate events or chunks on resubmission, missing work detected, merged and single-run results agree within a declared tolerance (mergeable reductions, deduplicated event IDs, per-chunk seeds). Automatic retries only with a configured maximum attempt count; absent config means no retries; repeated identical failures stop with state retained.
- Blinded values never appear in plots, logs, caches, or reports produced by the code.
- Scripts locate their files from their own path, write only to output paths they are given (creating or cleanly refusing folders), print JSON with a `status` key (interactive ROOT viewers on `--json`; the `inspect_root_file.C` macro is exempt), explain missing optional dependencies, and exit 0 ok, 1 negative verdict, 2 bad input, 3 missing dependency or incomplete (vocabulary: `core/status.py`).
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

1. Before any answer, even a quick one: use the profiles the user names, else those bound in `hep-research.project.json` at the project root; if present, run `python3 "<plugin root>/contracts/project.py" <project-dir> --preflight` and read the indexes it prints. Never infer an experiment or a model from vague wording; if a needed profile cannot be determined, ask which one.
2. Only when a profile is needed, read `<plugin root>/profiles/registry.json`, then that profile's `index.md`, then only the modules or dataset records the task needs. Never load an unrelated experiment or theory profile.
3. Local profiles live in the project (`local_profile_paths`), never in the plugin; `--preflight` checks them. A bound profile in neither place, or at a local path known to be a companion's, is used only via the installed `<plugin>:profile` skill that names it, after its preflight, from its folder; never scan for companions. If none is installed, the preflight fails, or a non-public profile lacks `agent_policy` approval for this host (none has it yet), say it is unavailable, do other work; never answer its topics from memory.
4. No profile needed: use general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, global cosmic-ray propagation fits): say so, then apply this skill's general discipline.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default ./hep-research-artifacts/), never the plugin, and pass `python3 "<plugin root>/contracts/validate.py" <artifacts_dir>`; no scratch. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it, except a Geant4 study record that passes the 3.1.0 upgrade rule.
6. Answer in the user's language; keep artifact fields, identifiers and file names in English. Name what you add or change for what it holds, in the project's terms, per `<plugin root>/skills/hep-computing/references/semantic-naming.md`; never rename an external (C4) name.
<!-- END context-resolution -->

## Resources

| Request | Read or run |
|---|---|
| Bug fix, feature, refactor, review | [playbook](references/engineering-playbook.md) |
| ROOT and PyROOT design | [ROOT design](references/root-balanced-design-guidelines.md) |
| Crashes, memory leaks | [crashes](references/crash-and-memory-debugging.md), [ROOT debugging](references/root-debugging.md) |
| uproot, awkward, RDataFrame, analysis pipelines | [Python HEP](references/python-hep-coding-patterns.md), [pipelines](references/analysis-data-pipelines.md) |
| Large or columnar data: Parquet, HDF5, chunked passes, memory | [columnar data](references/columnar-and-large-scale-data.md); `assets/chunked_histogram.py` |
| Slow or large code | [profiling](references/performance-profiling.md) |
| CMake and root-config builds | [CMake](references/cmake-and-build.md); `check_root_cpp_env.sh`, `new_root_cpp_project.sh` |
| SymPy, integrals, ODEs, convergence | [symbolic](references/symbolic-and-numerical-computation.md), [numerical](references/numerical-and-computational-methods.md) |
| Environments, containers, run manifests, data/MC version pairs per era; interpreter for package-dependent work | [environments](references/environments-and-containers.md); `environment_manifest.py` (`pairs`); `find_python.py` (`--python`, `HEP_RESEARCH_PYTHON`, caller, PATH) |
| Inspect or compare ROOT files; histogram errors, TEfficiency, RooWorkspace import, ROOT install | `inspect_root_file.py`, `compare_root_histograms.py`, `check_histogram_errors.py`, `summarize_histogram_statistics.py` (PyROOT or uproot); [ROOT usage](references/root-usage-patterns.md) |
| Partition, resubmit, merge | `local_partition.py`; Slurm and HTCondor: [batch scheduling](references/batch-scheduling.md) |
| Workflows (DAG, run record per step, Snakemake) | [workflows](references/analysis-workflows.md); `run_workflow.py`; `assets/workflow/` |
| Time-sliced records: deduplicate by key, then sum | `assets/time_slice_reduction.py`; [pipelines](references/analysis-data-pipelines.md) |
| CERN EOS storage | [CERN EOS](references/storage-cern-eos.md) |
| Analysis preservation: what to archive, rehearse a rerun | [preservation checklist](references/preservation-checklist.md) |
| Blinding checks of outputs, logs, caches | `audit_blinded_outputs.py` (synthetic sentinels only) |
| Naming, renames, naming review (any surface: charter, levels, change sets, report table) | [semantic naming](references/semantic-naming.md); `extract_names.py`, `<plugin root>/contracts/naming_check.py` |
| Implementation-ready research task | [tasks](references/task-authoring-guide.md); `lint_task.py` |
| Agile delivery, definition of done | [agile](references/agile-development-guide.md), [done](references/validation-and-done.md) |

Scripts in `<plugin root>/skills/hep-computing/scripts/` (read `--help` first; each is described in the [engineering playbook](references/engineering-playbook.md)); design guidelines: [Python](references/python-balanced-design-guidelines.md), [C++](references/cpp-balanced-design-guidelines.md), [Bash](references/bash-balanced-design-guidelines.md). Submission is unsandboxed execution: synthetic test environments only, each submission user-approved. Folder guide for people: [README.md](README.md).

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Physics meaning of a numerical result | hep-theory / hep-measurement | `computational-run` |
| Statistical interpretation | hep-statistics | `computational-run` |
| Model training issues | hep-ml | `ml-artifact` |
| Reports, figures, write-ups | hep-authoring | `computational-run` |

<!-- example: routing -->
- "Memory leak in my AMS-02 ntuple script" → this skill; the AMS profile is read only if the data format matters.
- "Build or run my analysis code against an experiment's software framework (setup script, compiler, framework program)" → this skill, plus the bound experiment profile's software modules when it has them.
<!-- /example -->
