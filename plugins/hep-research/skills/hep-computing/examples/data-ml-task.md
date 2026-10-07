# Gate `train_classifier.py` on a Split-Integrity Check

> Verified against the repository (`plugins/hep-research/`) on 2026-10-07. Paths are relative to the plugin root.

## Background

`skills/physics-ml/assets/train_classifier.py` is a training template that
"uses synthetic data so it runs immediately"; `make_dataloaders(args)` builds
`--train-size` (default 8000) and `--val-size` (default 2000) samples with no
sample IDs. `skills/physics-ml/scripts/check_split_integrity.py` checks a JSON
manifest of split IDs for exact overlap, duplicates within a split, group
leakage and temporal ordering, and exits nonzero on failure; its example
manifest `skills/physics-ml/assets/dataset-splits.example.json` fails on
purpose (one group, `p2`, in train and test, and one timestamp violation).
Nothing connects the two, so a user who replaces the synthetic data with a real
dataset can train on leaked splits without the check ever running.

## Objective

When a manifest is supplied, `train_classifier.py` refuses to start training if
the manifest fails the integrity check, and prints why; without a manifest it
behaves as today.

## Scope

### In Scope

- A `--split-manifest PATH` option on `train_classifier.py`.
- Calling the existing `check()` from `check_split_integrity.py`, not copying
  it.
- Tests for the passing, failing and absent-manifest cases.

### Out of Scope

- Changing what `check_split_integrity.py` checks.
- Real datasets, new models, hyperparameter changes.
- Near-duplicate or content-hash leakage detection.

## Repository Context

Verified by inspection on 2026-10-07:

- `skills/physics-ml/assets/train_classifier.py` is 237 lines, has argparse
  options including `--train-size`, `--val-size`, `--output-dir`, `--seed`,
  `--epochs`, `--device` and `--num-workers`, and no manifest option; it saves
  `last.pt` every epoch and `best.pt` on improvement.
- `skills/physics-ml/scripts/check_split_integrity.py` exposes
  `check(payload, strict=False)`, which returns a report whose status is
  `passed`, `failed` or `incomplete`, plus `find_overlaps`,
  `find_duplicates`, `find_group_leakage` and `find_temporal_violations`.
- `tests/skills/physics_ml/test_physics_ml_skill.py` imports `check` and the
  `find_*` functions and runs the script as a subprocess on the example
  manifest, asserting exit code 1 and `FAILED` and `group leakage` in the
  output; `tests/skills/physics_ml/test_assets_smoke.py` runs
  `train_classifier.py` on CPU (`--train-size 200 --val-size 50 --epochs 1`)
  and asserts that `best.pt` exists, skipping without PyTorch.
- `assets/` and `scripts/` are sibling folders of the skill; no file in
  `assets/` imports from `scripts/` today, and `tools/check_layering.py` says
  nothing about imports inside one skill.

## Technical Approach

1. Decide how `train_classifier.py` reaches `check_split_integrity` (import by
   path relative to `__file__`, or run the script as a subprocess); see Open
   Questions.
2. Add `--split-manifest`; if given, load the JSON, call `check()`, and exit
   nonzero with the report before any model or DataLoader is built.
3. Keep the default path equivalent in behavior to today's.
4. Add three tests next to `test_assets_smoke.py`: the shipped (failing)
   example manifest blocks training; a corrected manifest lets a short CPU run
   finish; no manifest runs as today.

## Deliverables

- Updated `skills/physics-ml/assets/train_classifier.py`.
- New tests in `tests/skills/physics_ml/`.
- A line naming the flag in `skills/physics-ml/references/deep-learning-guide.md`
  where the template is listed, if that list documents arguments (not checked
  here).

## Acceptance Criteria

- `python3 skills/physics-ml/assets/train_classifier.py --split-manifest skills/physics-ml/assets/dataset-splits.example.json`
  exits nonzero before the first epoch and the output names the group leak and
  the temporal violation.
- A manifest that passes the check allows training to start and finish a
  1-epoch CPU run with the same checkpoint file names (`best.pt`, `last.pt`)
  as without the flag.
- Without `--split-manifest`, the existing smoke test passes unchanged.
- No logic from `check_split_integrity.py` is duplicated in the training
  script.
- The pre-existing tests in `tests/skills/physics_ml/` still pass, with and
  without PyTorch installed (the new tests skip without it, like the smoke
  test).

## Validation

- Run `python3 -m unittest discover -s tests -t .` from the plugin root.
- Run the failing-manifest command above and read the output.
- Run a 1-epoch CPU training with a passing manifest.

## Open Questions

- The synthetic data has no sample IDs, so what does a manifest ID refer to?
  The flag only makes sense once the data source has IDs. **Requires
  Confirmation**; the task assumes the check gates the manifest and the user
  keeps it consistent with their own data loader.
- May a file in `assets/` import from `scripts/`? Both ship inside the one
  plugin directory, so the import works; whether templates meant to be copied
  out may depend on a sibling folder is a design question. **Requires
  Confirmation.**
- What should an unreadable or malformed manifest do? **TBD**; the task assumes
  it also exits nonzero with a message, before any model or output directory
  exists.
- Should a failing check be overridable (a `--force` flag)? **TBD**; none is
  assumed.

## References

- `skills/physics-ml/assets/train_classifier.py`
- `skills/physics-ml/scripts/check_split_integrity.py`
- `skills/physics-ml/assets/dataset-splits.example.json`
- `tests/skills/physics_ml/test_assets_smoke.py`
- `tests/skills/physics_ml/test_physics_ml_skill.py`
