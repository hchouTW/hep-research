# Migrating from the standalone skills

`hep-research` replaces seven standalone skills from `agentic-ai-skills@3e995a4`: `ams-analysis`, `hep-analysis`,
`deep-learning`, `academic-papers`, `academic-diagrams`, `agile-development` and `task-authoring`. Their content now
lives in the seven plugin skills, `core/`, `contracts/` and the `experiment:ams-02` profile. Where each legacy file
went, and why, is in `docs/migration-map.csv` (source path, commit, destination, disposition, rationale).

| Legacy skill | Now |
|---|---|
| `ams-analysis` | `experiment:ams-02` profile (modules, evidence ledger, scripts); generic statistics in `core/stats` and `hep-statistics`; kinematics in `core/kinematics` |
| `hep-analysis` | split between `hep-analysis`, `detector-response`, `hep-theory`, `hep-statistics` and `hep-computing` by deliverable |
| `deep-learning` | `physics-ml` |
| `academic-papers`, `academic-diagrams` | `research-communication` |
| `agile-development`, `task-authoring` | `hep-computing` |

The legacy folders are snapshots: they are not updated, and fixes go only into the plugin.

## Coexistence

Both can be installed at once. Plugin skills are namespaced (`/hep-research:hep-statistics`) and never overwrite a
standalone skill folder; installing and removing the plugin left the seven legacy folders byte-identical in the G5
test. Claude may still pick a legacy skill for some requests while both are installed (7 of 48 live routing cases
in that test), so for consistent behavior either name the plugin skill or disable the legacy ones.

## Disabling the legacy skills

Standalone skills are folders under `~/.claude/skills/` (user) or `<project>/.claude/skills/` (project). To disable
one without deleting it, move the folder out of that directory, for example to `~/.claude/skills-disabled/`, and
start a new session. Keep the folder: it is your rollback.

## Rollback

1. `claude plugin uninstall hep-research@hep-research-dev` (and `claude plugin marketplace remove hep-research-dev`).
2. Move the legacy skill folders back into the skills directory.
3. Start a new session.

Your project files (`hep-research.project.json`, `artifacts_dir`, local profiles) live in the project and are not
touched by install, removal or rollback. Artifacts written by the plugin are JSON and remain readable; the legacy
AMS skill's YAML or JSON specifications can be converted forward with
`profiles/experiments/ams-02/scripts/convert_legacy_spec.py`.

## Differences you may notice

- Results carry status labels (`synthetic`, `asimov`, `observed`, `preliminary`, `failed`, `unvalidated`,
  `user-supplied`) that downstream results and write-ups must keep.
- Comparisons between a prediction and a measurement go through a comparison gate that refuses mismatched
  observables, units, levels or conventions instead of comparing them anyway.
- A citation newer than a ledger's verification date is reported as unverified rather than as likely nonexistent.
