Nine worked Task Markdown outputs: one per category (feature, bug, performance,
research) from the original authoring workflow this skill was built from, three
added on 2026-10-02 (migration, agentic loop, data/ML), plus two analysis
requests. Each follows [../assets/task-template.md](../assets/task-template.md)
exactly and demonstrates the Confirmed / Inferred / Unresolved distinction from
the [task authoring guide](../references/task-authoring-guide.md) with a
non-trivial Open Questions section; none of them mark an unknown as resolved just
to look complete. The tests check that every `*-task.md` here carries the 12
required sections in order.

<!-- example: experiment-specific illustration -->
**These are historical snapshots.** All of them were written against the legacy
skills repository (`agentic-ai-skills` at the pinned commit `3e995a4`, seven
standalone skills) as the inspected repository, so every Repository Context claim
was a real, verified fact about that repository when written. Paths they cite
(for example `academic-papers/...`, `deep-learning/...`, `task-authoring/...`)
refer to that repository, not to this plugin; `lint_task.py` resolves them against
a legacy checkout (`tasks/hep-research/scripts/fetch_legacy.sh`). Read them for
their structure, not their paths.
<!-- /example -->

| Example | Category | Scenario | Open Questions highlight |
|---|---|---|---|
| [feature-task.md](feature-task.md) | Feature | Adding a `--format json` output mode to all seven skills' `validate_skill_bundle.py`, whose text outputs differ in four wordings and one takes a path argument | Whether the JSON shape should live in one shared module (skills install as separate folders), and whether any consumer exists |
| [bug-task.md](bug-task.md) | Bug | `academic-papers`' bundle validator ignores `agents/openai.yaml`: deleting it still prints "passed all checks" (reproduced), although `task-authoring`'s validator requires the same file | Whether the file is required or optional (the README says "optional"), nobody has stated the intent |
| [performance-task.md](performance-task.md) | Performance | "Create a task for RICH reconstruction performance analysis" - the authoring reference's own worked example, run against this repository | This repository has no RICH reconstruction code, dataset, or baseline at all - nearly every implementation detail is marked Unresolved rather than invented |
| [research-task.md](research-task.md) | Research | Whether the three near-copy `behavior_eval.py` harnesses (similarity 0.83-0.95) should be consolidated, given the `cp -r` per-skill install | Whether the harnesses run only from a checkout or also from an installed skill folder |

Three examples cover categories the first four did not:

| Example | Category | Scenario | Open Questions highlight |
|---|---|---|---|
| [migration-task.md](migration-task.md) | Migration | Dropping `orders.legacy_id` in the demo shop under `tests/fixtures/shop_repo/`; irreversible, so backup and restore are acceptance criteria | Outside readers of the column, and whether a backup is a sufficient rollback |
| [agentic-loop-task.md](agentic-loop-task.md) | Agentic loop | A bounded retry-until-complete mode for `tests/behavior_eval.py run`; names the pattern, termination, early-stop and cap | The maximum number of passes is TBD (none was given) |
| [data-ml-task.md](data-ml-task.md) | Data / ML | Gating `deep-learning/assets/train_classifier.py` on `check_split_integrity.py` | The synthetic data has no sample IDs, so what a manifest ID refers to is unresolved |

<!-- example: experiment-specific illustration -->
Two further examples target `hep-analysis` domain requests specifically -
still Task Markdown outputs against this same repository, but chosen to
contrast a request the repository genuinely cannot fulfill (no CMS analysis
code or data exists here) against one it already has real, working building
blocks for (the AMS-02 scripts and their tests):
<!-- /example -->

<!-- example: experiment-specific illustration -->
| Example | Category | Scenario | Open Questions highlight |
|---|---|---|---|
| [cms-higgs-analysis-task.md](cms-higgs-analysis-task.md) | Research | "Create a task for a CMS experiment Higgs boson analysis" - this repository has no CMS dataset, MC, or channel-specific code, only generic Combine/pyhf templates and likelihood/inference guidance | Which Higgs channel to target, and whether `pyhf`/ROOT/Combine are expected to be installed in the execution environment (confirmed absent/broken in the one checked here) |
| [ams-antiproton-analysis-task.md](ams-antiproton-analysis-task.md) | Feature | Composing the five existing, individually-tested AMS-02 building-block scripts into one antiproton/proton-ratio worked pipeline - fully completable in this repository, unlike the RICH and CMS-Higgs examples above | Whether `--demodulate` support, a new `scripts/pipelines/` layout, and a matching `hep-analysis/examples/` entry are wanted alongside the script |
<!-- /example -->
