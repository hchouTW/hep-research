# Add a `--format json` Output Mode to Each Skill's `validate_skill_bundle.py`

> Verified against the repository on 2026-10-02 (seven skills). Replaces the 2026-09-12 version, which assumed five skills with one shared output shape.

## Background

Seven skills in `agentic-ai-skills` each ship their own
`scripts/validate_skill_bundle.py`: `academic-diagrams`, `academic-papers`,
`agile-development`, `ams-analysis`, `deep-learning`, `hep-analysis` and
`task-authoring`. Each prints free text and uses the exit code as the only
machine-checkable signal, and the text is not the same across skills
(confirmed by reading the `print(` calls on 2026-10-02):

- `agile-development`, `deep-learning`, `hep-analysis`, `task-authoring`:
  `missing files:` / `empty files:` lists on failure.
- `academic-diagrams`: `Bundle problems:` then one indented line per problem,
  and `Bundle OK: N files present and non-empty.` on success.
- `ams-analysis`: `Bundle FAILED:` / `Bundle OK: N required files present,
  links and anchors resolve.`
- `academic-papers`: `FAILED: N issue(s) in <path>` / `OK: <path> passed all
  checks.`, takes an optional positional skill-root path, and exits 2 with an
  `error:` line on stderr when that path is not a directory.

A maintainer who wants to aggregate results across the skills has to parse
four different wordings, which breaks on any wording change.

## Objective

Each of the seven `validate_skill_bundle.py` scripts accepts an optional
`--format json` flag that prints one machine-readable JSON object with the
same keys in every skill, while the default invocation keeps its current
output and exit codes unchanged.

## Scope

### In Scope

- Add `--format {text,json}` (default `text`) to the seven scripts.
- Define one JSON shape used identically by all seven.
- Add tests for the flag in each skill's `tests/` directory.
- Add one `--format json` line to each skill's `README.md` "Quick checks"
  section (six READMEs have one; `academic-papers/README.md` calls it
  "Verifying this skill bundle", confirmed by grep on 2026-10-02).

### Out of Scope

- Wiring this into CI: there is no `.github/` directory and no `*.yml` file in
  the repository (confirmed 2026-10-02).
- A cross-skill aggregator script.
- Changing the default text output, its wording, or any exit code, including
  `academic-papers`' exit 2.
- Making the seven scripts share code (see Open Questions).

## Repository Context

Verified by inspection on 2026-10-02:

- The seven scripts exist at `<skill>/scripts/validate_skill_bundle.py`
  (139, 143, 102, 217, 140, 193 and 169 lines for academic-diagrams,
  academic-papers, agile-development, ams-analysis, deep-learning,
  hep-analysis and task-authoring). None imports `argparse` or reads
  `sys.argv`, except that `academic-papers` passes `sys.argv[1:]` to its
  `main(argv)`.
- Each skill has its own `tests/` directory run from inside the skill folder
  with `python3 -m unittest discover -s tests -v` (root `README.md`,
  "Verifying a skill bundle"). Test file names differ per skill
  (for example `test_agile_skill.py`, `test_bundle.py`,
  `test_skill_bundle.py`); `hep-analysis/tests/` has several unrelated test
  files and was not searched for the one covering the validator.
- `task-authoring`'s script additionally checks the 12-section contract of
  `templates/task-template.md`; `ams-analysis`'s checks that links and anchors
  resolve. The JSON shape has to carry such extra problems.
- Not read in full for this task: the `hep-analysis`, `deep-learning` and
  `academic-diagrams` scripts beyond their `print(` lines.

## Technical Approach

1. Read all seven scripts in full and list each failure and success branch.
2. Fix one JSON shape, for example
   `{"ok": bool, "skill": str, "problems": [str]}`, where `problems` holds the
   same strings the text mode prints (missing and empty files included), so
   no skill needs its own keys.
3. Add `--format` parsing to each script. Use `argparse` where the script
   takes no arguments; for `academic-papers` keep the optional positional
   path working.
4. In `json` mode print one JSON object to stdout and keep the exit codes
   (0 ok, 1 problems, and 2 for `academic-papers`' bad path, where the JSON
   object is still printed).
5. Add tests per skill: the shipped bundle gives `"ok": true` and parses with
   `json.loads`; a doctored scratch copy (the pattern already used in
   `task-authoring/tests/test_task_authoring_skill.py`) gives `"ok": false`
   with the expected problem.
6. Add one example invocation to each README's bundle-check section.

## Deliverables

- Seven updated `scripts/validate_skill_bundle.py`.
- Seven updated `README.md` sections (six "Quick checks", one "Verifying
  this skill bundle").
- New or extended tests in the seven `tests/` directories.
- A short note in each skill's `VALIDATION.md` (all seven exist) saying what
  was added and run.

## Acceptance Criteria

- With no arguments, each script's stdout and exit code on the shipped bundle
  are byte-identical to before (capture both before editing and diff).
- `--format json` prints exactly one JSON object that `json.loads` parses,
  with keys `ok`, `skill` and `problems` and the same types in all seven.
- On a doctored bundle (a deleted required file) `--format json` reports
  `"ok": false` and a non-empty `problems`, and the exit code is non-zero.
- `academic-papers --format json` on a missing path exits 2 and still prints a
  JSON object with `"ok": false`.
- `python3 -m unittest discover -s tests` passes in all seven skills.

## Validation

- In each skill folder run `python3 scripts/validate_skill_bundle.py` and
  `python3 scripts/validate_skill_bundle.py --format json`; compare the first
  with the pre-change capture.
- Run `python3 -m unittest discover -s tests` in each skill folder.
- Run a doctored scratch copy of one skill per output family (the four
  wordings above) through both modes.

## Open Questions

- Should the shape live in one shared module instead of seven copies? Each
  script is standalone today; sharing would add a cross-skill import, which
  conflicts with skills being installed one at a time. **Requires
  Confirmation.**
- Is there a consumer for this JSON (a CI job, a dashboard)? **TBD**: none
  exists in the repository and the requester named none.
- Should `problems` keep the exact text strings, or be split into
  structured fields (`missing`, `empty`, `broken_links`)? **TBD**; the
  simple shape above is assumed because the four families differ.

## References

- `README.md` (repository root), "Verifying a skill bundle".
- `agile-development/scripts/validate_skill_bundle.py` and
  `academic-papers/scripts/validate_skill_bundle.py`: the two ends of the
  existing variation (list-style output and a path argument with exit 2).
- `task-authoring/tests/test_task_authoring_skill.py`: the scratch-copy test
  pattern.
