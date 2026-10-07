# Decide Whether `lint_task.py` Should Accept a Cited Path Whose Directory Is Wrong

> Verified against the repository (`plugins/hep-research/`) on 2026-10-07. Paths are relative to the plugin root.

## Background

`skills/hep-computing/scripts/lint_task.py` lints a generated Task Markdown
file. One of its checks is that every backtick path that looks like a
repository file exists under `--repo`. The check, `path_exists()`, first strips
an installed-skill prefix (`.claude/skills/<name>/` and the Codex, Gemini and
`.agents` equivalents), then accepts the path if `repo / rel` exists, and
otherwise accepts it if **any** file under the repository with the same base
name ends with the cited path after dropping one or more leading segments:

```python
hits = [hit.as_posix() for hit in repo.rglob(parts[-1]) if ...]
return any(
    hit.endswith("/" + "/".join(parts[start:])) for hit in hits for start in range(len(parts) - 1)
)
```

The module docstring documents the intent: "so skill-relative and
repo-name-prefixed paths resolve". The consequence, reproduced on 2026-10-07: a
task that cites `skills/hep-theory/scripts/lint_task.py` (no such file; the
script lives in `hep-computing`) passes with 0 errors, because the suffix
`scripts/lint_task.py` matches the real file, while
`skills/hep-computing/scripts/ghost.py` is correctly reported as an error. A
task author who puts a real script in the wrong skill folder is therefore not
caught, which is exactly the kind of mechanical defect the linter exists for.

## Objective

`lint_task.py` has one documented, tested rule for how much of a cited path must
match a real file: either suffix matching is kept and the minimum matched prefix
is stated (and a wrong skill folder for a real file name is reported at least as
a warning), or suffix matching is limited to the cases the docstring names
(installed-skill and repository-name prefixes) and a wrong directory is an error.

## Scope

### In Scope

- Decide, with the maintainer, which of the two behaviors is intended.
- Implement it in `path_exists()` and state it in the module docstring.
- Add regression tests in `tests/skills/hep_computing/test_lint_task.py` for a
  wrong-directory citation of a real file name.
- Re-lint the shipped examples under `skills/hep-computing/examples/` against
  the plugin root and fix any citation the stricter rule rejects.

### Out of Scope

- `PATH_RE`, which only matches paths with a file extension; directory paths
  such as `skills/physics-ml/assets/` and extension-less files are never
  checked. That is a separate gap, noted here and not fixed.
- The section, placeholder and loop-limit checks of the linter.
- `validate_skill_bundle.py` and `check_template_sections()`, which the linter
  imports but does not change.

## Repository Context

Verified by inspection on 2026-10-07:

- `skills/hep-computing/scripts/lint_task.py` defines `PATH_RE`, `SKIP_PATH`
  and `path_exists()` as described; the suffix loop runs `start` from 0 to
  `len(parts) - 2`, so the shortest accepted suffix is the last two segments
  (`<dir>/<file>`).
- A scratch task citing `skills/hep-theory/scripts/lint_task.py` in its
  Background produced `0 error(s)` with `--repo` set to the plugin root; the
  same task citing `skills/hep-computing/scripts/ghost.py` produced
  `ERROR: cited path does not exist`.
- `tests/skills/hep_computing/test_lint_task.py` builds a one-file repository
  (`app/users_api.py`) and covers a missing path
  (`test_missing_repo_path_is_an_error`), a path named as absent
  (`test_missing_path_named_as_absent_is_only_a_warning`) and the no-`--repo`
  case; no test cites a real file name in a wrong directory.
- `lint()` also resolves paths against the skill bundle itself
  (`skill_root`), so a task may cite the authoring references it used; that
  second lookup goes through the same `path_exists()`.
- The five shipped examples cite plugin paths; whether any of them relies on
  suffix matching was not checked before this task.

## Technical Approach

1. Ask the maintainer which behavior is intended (Open Questions).
2. If suffix matching stays: require that the matched suffix cover at least the
   two segments after the skill or package folder, or report a wrong-directory
   match as a warning naming the file it matched. Record the rule in the
   docstring.
3. If it goes: keep only the installed-skill prefix strip and an optional
   repository-name prefix (the first segment equal to `repo.name`), and treat
   everything else as a plain existence check.
4. Add tests to `LintTests`: a repository with `pkg/a/tool.py`, a task citing
   `pkg/b/tool.py`, asserting the chosen result (error, or warning with the
   matched file in the message).
5. Run the linter on every `skills/hep-computing/examples/*-task.md` with
   `--repo <plugin root>` and fix any citation the new rule rejects.

## Deliverables

- Updated `skills/hep-computing/scripts/lint_task.py` (code and docstring).
- New tests in `tests/skills/hep_computing/test_lint_task.py`.
- Corrected example citations, if any, under `skills/hep-computing/examples/`.

## Acceptance Criteria

- A task citing a real file name in a wrong directory is reported (error or
  warning, per the decision) and a test asserts exactly that.
- An installed-skill-prefixed citation (`.claude/skills/hep-computing/scripts/lint_task.py`)
  still resolves, as the docstring promises; a test asserts it.
- The existing tests in `test_lint_task.py` pass unchanged.
- Every shipped example lints with 0 errors against the plugin root.

## Validation

- `python3 -m unittest tests.skills.hep_computing.test_lint_task` from the
  plugin root.
- Repeat the scratch-task experiment with the wrong-directory and the
  wrong-file-name citations and confirm the outputs match the decision.
- `for f in skills/hep-computing/examples/*-task.md; do python3 skills/hep-computing/scripts/lint_task.py "$f" --repo .; done`.

## Open Questions

- Is suffix matching a feature (tasks written from inside one skill folder cite
  `scripts/x.py`, and tasks from a parent checkout prefix the repository name)
  or an accident of the installed-skill case? **Requires Confirmation.**
- If kept, how many segments must match? Two (today) lets any `scripts/x.py`
  match any skill; three would require the skill folder. **TBD.**
- Should the extension-less and directory gap of `PATH_RE` be handled in the
  same change? **TBD**; out of scope as written.

## References

- `skills/hep-computing/scripts/lint_task.py`: `path_exists()`, `PATH_RE`,
  the module docstring.
- `tests/skills/hep_computing/test_lint_task.py`: the existing path tests.
- `skills/hep-computing/references/task-quality-checklist.md`: what the
  linter does not judge.
