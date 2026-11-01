# Event display for <project>
<!-- Task card for one event display. Fill every <...>; write TBD where a value is not known. An agent given this
file runs it autonomously: references/event-displays.md §4 step by step, each step's "Done when" checked before
the next, stopping only at the rules under Acceptance Criteria. Sections follow assets/task-template.md; lint with
scripts/lint_task.py <this file> --repo <project root>. -->

**Run settings.** A setting left as `<...>` takes its default; a `<...>` left anywhere else in the card that the
agent cannot fill from the files is a stop-and-ask item.

| Setting | Value | Default |
|---|---|---|
| Project root | `<path>` | the folder that holds `hep-research.project.json` |
| Templates copy | `<project>/display/` | `display/` in the project root, copied from `<plugin root>/skills/hep-computing/assets/event-display/` |
| Python | `<interpreter>` | a venv in the project with numpy, uproot, awkward, playwright (the latter's Chromium installed) |
| Node | `<version>` | the newest installed, at least 22 |
| Installs | `<allowed / not allowed>` | allowed into the project's venv and `npm ci` in `display/web` only; never system-wide |
| Fix rounds | `<per step / total>` | 3 per failing step, 8 in total |
| Status labels of inputs | `<labels>` | `unvalidated` |

## Background
<!-- Why the page is needed and for whom. -->

## Objective
<!-- One or two sentences: what the page shows, to whom, where it is served. -->

## Scope

### In Scope
- Events: `<file(s)>`, `<which events: --entries A:B or --events RUN_SUBRUN_EVENT,...; at most limits.max_events of
  the mapping, 50 by default>`, default event `<run_subrun_event>`.
- Panels: see the table in Technical Approach.

### Out of Scope
- Computing or re-binning any result for the page (rule 1 of the guide).
- <other exclusions>

## Repository Context
<!-- Verified paths only: event files, result files, their producers (run records), the project's
hep-research.project.json and artifacts_dir, policy or blinding notes. Write "not found" for anything expected
but absent. -->

| Item | Path | Producer (run record or person) | Unit / frame | Status label |
|---|---|---|---|---|
| Events | | | | |
| Geometry | | | mm | |
| Result: <name> | | | | |

## Technical Approach

Plan-and-Solve: the steps of `references/event-displays.md` §4, in order, each checked by its "Done when" before
the next. Resuming after an interruption: rerun from the first step whose "Done when" does not hold, into an
empty output folder (move the old one aside first: the exporters add to an existing folder; only `build_bundle.py`
replaces `bundle/`).

| Panel id | Title | Integration | Binding (event / dataset / static) | Source result (spec `source`) | Errors (auto / disabled: reason) |
|---|---|---|---|---|---|
| | | | | | |

Branch mapping (step 2): `<branch>` → `<collection>` (`Point` or `Line`), unit `<mm|cm|m|um>`.

Fix loop for a failing step: read the tool's JSON output; change only the copies in `display/` or the spec, never a
result, a payload or a check; rerun the step. Each rerun after a change is one fix round.

## Deliverables
- `<project>/display/` (adapted templates, `web/package-lock.json`) and the built `bundle/`.
- A `computational-run` artifact in the project's artifacts_dir (inputs with sha256, commands, tool versions, outputs,
  check results), passing `python3 "<plugin root>/contracts/validate.py" <artifacts_dir>`.
- A hand-off note in the form of `assets/completion-summary.md`: status (`done`, `incomplete` or `stopped`), how to
  serve (HTTPS, or loopback only), labels, coverage gaps, every check with its result, fix rounds used, anything not run and why, and what the
  checks do not prove.

## Acceptance Criteria
- `check_bundle.py bundle --spec bundle-spec.json` (with `unchecked_sources` empty) and `test_page.py bundle` both
  report `ok`; every check is listed in the hand-off.
- Every line of `references/event-display-checklist.md` is ticked with evidence, or reported as not done.
- Each panel's readback equals its payload; events without a result show "unavailable", never zero.
- Status labels of the inputs appear on the page and in the run record.
- Termination: status `done` when every criterion above holds; `incomplete` when a step could not run for lack of a
  tool (Node, Chromium) under the run settings, with the reason.
- Iteration limit: the fix rounds in the run settings; on reaching either limit, stop with `stopped` and the last
  output.
- Early stopping, then ask with the evidence: a unit or frame is unknown; a result has no producer; policy or blinding
  does not clearly allow the data in a static page; an exporter refuses (resolve upstream, never by editing a
  payload); the same step fails twice with identical output after two different changes; a fix would change a
  result, a payload or a check.

## Validation
- `python3 export_histogram.py --self-test`, `python3 check_bundle.py bundle --spec bundle-spec.json`,
  `python3 test_page.py bundle`.
- Open the served page (loopback) and look at it: event visible, titles readable, panels follow the selected event.

## Open Questions
- <only what changes the build; write TBD, do not invent values>

## References
- `<plugin root>/skills/hep-computing/references/event-displays.md`, `event-display-facts.md`, `event-display-checklist.md`
