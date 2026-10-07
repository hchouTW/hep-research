Five worked Task Markdown outputs, one per category this skill distinguishes
beyond a plain feature request (bug, research, migration, agentic loop,
data/ML), all written against this plugin (`plugins/hep-research/`) as the
inspected repository. Each follows [../assets/task-template.md](../assets/task-template.md)
exactly and demonstrates the Confirmed / Inferred / Unresolved distinction from
the [task authoring guide](../references/task-authoring-guide.md) with a
non-trivial Open Questions section; none of them mark an unknown as resolved just
to look complete. The tests check that every `*-task.md` here carries the 12
required sections in order and that every repository path it cites exists
(`scripts/lint_task.py --repo <plugin root>`).

Every Repository Context claim was a verified fact about this plugin on the date
in the file's first line. Paths are relative to the plugin root. The plugin keeps
moving, so re-verify before reusing a claim; read the examples for their
structure and for how they separate what was checked from what was not.

| Example | Category | Scenario | Open Questions highlight |
|---|---|---|---|
| [bug-task.md](bug-task.md) | Bug | `scripts/lint_task.py` accepts a cited path whose directory is wrong when a file of the same name exists elsewhere in the repository (reproduced), so a task can cite `skills/hep-theory/scripts/lint_task.py` without an error | Whether suffix matching is a feature (installed-skill prefixes) or a defect, and how many segments must match |
| [research-task.md](research-task.md) | Research | Whether the report-writing and artifact scaffolding repeated across the twelve `examples/*/run.py` scripts should become one shared helper | Whether an example may import anything outside its own folder, given that each is meant to be read as a self-contained worked example |
| [migration-task.md](migration-task.md) | Migration | Dropping the hand-written display fields `year_text`, `tier_text` and `locator_text` from the evidence source ledgers; irreversible for the text that is not derivable from the structured fields, so an export and a restore path are acceptance criteria | Whether the non-derivable texts (`5-6` tier ranges, dual-year entries) are content to keep in a structured form or display noise to drop |
| [agentic-loop-task.md](agentic-loop-task.md) | Agentic loop | A bounded resubmit step inside `core/partition/campaign.py`'s `watch()` loop; names the pattern, termination, early-stop and cap | Whether a resubmission inside `watch` may ever be approved by configuration rather than by a flag on each run |
| [data-ml-task.md](data-ml-task.md) | Data / ML | Gating `skills/physics-ml/assets/train_classifier.py` on `scripts/check_split_integrity.py` | The synthetic data has no sample IDs, so what a manifest ID refers to is unresolved |
