# Decide Whether `academic-papers`' Bundle Validator Should Require `agents/openai.yaml`

> Verified against the repository on 2026-10-02. Replaces the 2026-09-12 version, whose scenario (`examples/` paths skipped by the same regex) no longer applies because `academic-papers/examples/` was removed.

## Background

`academic-papers/scripts/validate_skill_bundle.py` checks that `SKILL.md` has
frontmatter, that the frontmatter `name` matches the folder, that backtick
paths in `SKILL.md` exist, that every file under `references/`, `scripts/` and
`assets/` is mentioned in `SKILL.md`, and that scripts parse. Its path regex is:

```python
BACKTICK_PATH_RE = re.compile(r"`((?:references|scripts|assets)/[^`\s]+)`")
```

and the orphan check loops over `("references", "scripts", "assets")`. The
skill also ships `agents/openai.yaml` (Codex UI metadata) and `tests/`, which
neither check looks at. Deleting `agents/openai.yaml` from a copy of the bundle
still prints `OK: ... passed all checks.` and exits 0 (reproduced 2026-10-02).
`README.md` describes the file as "optional Codex UI metadata", so the
silence may be intended; nothing in the validator's docstring says so either
way.

## Objective

`validate_skill_bundle.py` has one documented, tested behavior for
`agents/openai.yaml`: either it must exist (and, if present, be non-empty), or
its absence is documented as acceptable and a test asserts that.

## Scope

### In Scope

- Decide, with the maintainer, whether the file is required or optional.
- Implement that decision in `academic-papers/scripts/validate_skill_bundle.py`
  and state it in the module docstring's "Checks" list.
- Add a regression test for the chosen behavior.

### Out of Scope

- Validating the YAML content of `agents/openai.yaml`.
- Checking `tests/`, and the other skills' validators (each skill has its own;
  `task-authoring`'s lists `agents/openai.yaml` in `REQUIRED_PATHS`).
- Changing the exit codes (the docstring says 0 or 1; `main()` also returns 2
  with an `error:` line when the path is not a directory, which the docstring
  does not mention; that mismatch is a separate, smaller fix).

## Repository Context

Verified by inspection on 2026-10-02:

- `academic-papers/scripts/validate_skill_bundle.py` defines
  `BACKTICK_PATH_RE` as above; `check_referenced_paths_exist()` applies it and
  `check_no_orphaned_files()` iterates the three directories.
- `academic-papers/agents/openai.yaml` exists. `SKILL.md` does not mention it;
  `README.md` mentions it at its file-tree entry and in the per-agent
  invocation notes.
- A scratch copy of the bundle with `agents/openai.yaml` deleted produced
  `OK: <path> passed all checks.` and exit code 0.
- `academic-papers/tests/test_skill_bundle.py` has `TestRealBundle` (runs the
  validator on the real bundle) and `TestSyntheticBundles` (synthetic bundles
  in a temporary directory, e.g. `test_orphaned_file_detected`,
  `test_valid_minimal_bundle`). No case covers `agents/`.
- `task-authoring/scripts/validate_skill_bundle.py` lists `agents/openai.yaml`
  in its required files, so the two skills currently disagree.

## Technical Approach

1. Ask the maintainer which behavior is intended (Open Questions).
2. If required: add an `agents/openai.yaml` existence (and non-empty) check
   to `validate()` and an entry in the docstring's "Checks". The real bundle
   must still pass.
3. If optional: say so in the docstring ("`agents/` is intentionally
   unchecked") and keep the code as is.
4. Add a test to `TestSyntheticBundles`: a minimal valid synthetic bundle with
   and without `agents/openai.yaml`, asserting the chosen result.

## Deliverables

- Updated `academic-papers/scripts/validate_skill_bundle.py` (code or
  docstring, per the decision).
- One new test in `academic-papers/tests/test_skill_bundle.py`.
- A short note in `academic-papers/VALIDATION.md` giving the decision and
  what was run.

## Acceptance Criteria

- A synthetic minimal bundle without `agents/openai.yaml` is rejected (if
  required) or accepted with the choice documented in the docstring (if
  optional), and a test asserts exactly that.
- `python3 scripts/validate_skill_bundle.py` still exits 0 on the unmodified
  `academic-papers` bundle.
- The existing checks (frontmatter, name, referenced paths, orphans, syntax)
  behave as before; the existing tests pass.
- `python3 -m unittest discover -s tests -v` passes from `academic-papers/`.

## Validation

- Run the unit tests from `academic-papers/`.
- Run the validator on the real bundle and expect `passed all checks`.
- Repeat the scratch-copy experiment (copy the skill, delete
  `agents/openai.yaml`, run the validator) and confirm the result matches the
  decision.

## Open Questions

- Is `agents/openai.yaml` required for `academic-papers`, as it is for
  `task-authoring`, or genuinely optional as its README says? **Requires
  Confirmation.** Nobody has stated the intent.
- If required, should the check only test existence, or also that the file is
  non-empty? **TBD.**
- Should the `examples`-style gap for other unchecked directories (`tests/`)
  be handled together? **TBD**; out of scope as written.

## References

- `academic-papers/scripts/validate_skill_bundle.py`: the regex, the orphan
  check and the docstring.
- `academic-papers/tests/test_skill_bundle.py`: the synthetic-bundle tests.
- `academic-papers/README.md`: the "optional" wording for `agents/openai.yaml`.
- `task-authoring/scripts/validate_skill_bundle.py`: the sibling that requires
  the file.
