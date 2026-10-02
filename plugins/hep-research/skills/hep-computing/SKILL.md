---
name: hep-computing
description: "Use when the deliverable is working, reproducible scientific software or its execution: writing, debugging and reviewing physics code (Python, C++, ROOT/PyROOT, uproot/awkward, RDataFrame), crashes and memory leaks, CMake builds, data I/O and formats, performance, symbolic and numerical computation (SymPy, integration, ODEs, convergence and tolerance studies), environment and run manifests, partitioning, batch submission, merging and recovery, blinding enforcement in outputs and logs, and authoring an implementation-ready research task. Also small, verified, reviewable code changes. Applies even when the code belongs to a named experiment. Not for deciding the physics or statistics itself: measurement design (hep-analysis), detector performance (detector-response), derivations (hep-theory), inference (hep-statistics), ML model design (physics-ml)."
---

# hep-computing: scientific software and execution

**Owns:** scientific software, symbolic and numerical execution, builds, I/O, debugging, performance, manifests, partition/merge/recovery, reproducibility, blinding enforcement in outputs, logs and caches, research-task authoring; stewardship of `core/bootstrap`, `core/binned`, `core/blinding`.
**Typical artifacts:** code, `computational-run` (inputs with checksums, tool versions, commands, environment, seeds, tolerances, exit status, output hashes), output audits.
**Never:** treat a successful run as scientific validity; install software system-wide or fetch from the network without the user's approval.

## Invariants

- Execution success is not scientific validity; a run that terminates has not necessarily converged. Report tolerances and refinement studies.
- Record what is needed to reproduce: input checksums, tool and library versions, exact commands, seeds, tolerances, environment.
- Partitioned work uses a manifest: no duplicate events or chunks on resubmission, missing work detected, merged and single-run results agree within a declared tolerance. Automatic retries only with a configured maximum attempt count; absent config means no retries; repeated identical failures stop with state retained.
- Blinded values never appear in plots, logs, caches, or reports produced by the code.
- Scripts locate their files from their own path, take an explicit output directory, emit an exit code plus a JSON status, and explain missing optional dependencies.
- Changes are small and verifiable: state acceptance criteria and how they were checked; keep diffs surgical.
- Failures (missing tools or licenses, nonconvergence, invalid outputs) are explicit statuses passed downstream.

## Workflow

1. Resolve context (stanza below); load an experiment profile only for experiment-specific data formats or conventions the code needs.
2. Reproduce the problem or define the run; capture the environment.
3. Make the smallest change that fixes or implements it; add or run a test.
4. Record the `computational-run` artifact for durable results.

<!-- BEGIN context-resolution: generated from contracts/stanzas/context-resolution.md by tools/build_stanzas.py; do not edit -->
## Context resolution

1. Use the profiles the user names explicitly. Otherwise read `hep-research.project.json` in the project root, if it exists. Never infer an experiment or a model from vague wording. If the task needs a profile and none can be determined, ask which one.
2. Only when a profile is needed, read `${CLAUDE_PLUGIN_ROOT}/profiles/registry.json` (a short index), then that profile's `index.md`, then only the modules or dataset records the task needs. Experiment and theory profiles are independent: load neither unless the task needs it, and never load an unrelated experiment.
3. Local profiles named in the project config live in the project and are checked with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/project.py" <project-dir>`; never copy them into the plugin.
4. No profile needed: proceed with general methods. Domain without a validated profile (for example lattice QCD, EFT global fits, cosmic-ray propagation): say so explicitly, then apply the general discipline of this skill.
5. Durable results and handoffs are files in the project's `artifacts_dir` (default `./hep-research-artifacts/`), never inside the plugin. Check them with `python3 "${CLAUDE_PLUGIN_ROOT}/contracts/validate.py" <artifact.json>`. Keep every status label (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`, `user-supplied`) on everything derived from it.
<!-- END context-resolution -->

## Resources

Engineering-discipline, ROOT design, build, debugging, numerical-methods and research-task-authoring references arrive in M2 under `references/`. Optional tool adapters live in `${CLAUDE_PLUGIN_ROOT}/adapters/` and are `proposed` until tested in a declared environment.

## Handoffs

| Need | Hand to | Artifact |
|---|---|---|
| Physics meaning of a numerical result | hep-theory / hep-analysis | `computational-run` |
| Statistical interpretation | hep-statistics | `computational-run` |
| Model training issues | physics-ml | `ml-artifact` |

<!-- example: routing -->
- "Memory leak in my AMS-02 ntuple script" → this skill; the AMS profile is read only if the data format matters.
<!-- /example -->
