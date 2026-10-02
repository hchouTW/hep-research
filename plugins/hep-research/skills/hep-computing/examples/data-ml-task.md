# Gate `train_classifier.py` on a Split-Integrity Check

> Verified against the repository on 2026-10-02.

## Background

`deep-learning/assets/train_classifier.py` is a training template that "uses
synthetic data so it runs immediately"; `make_dataloaders(args)` builds
`--train-size` (default 8000) and `--val-size` (default 2000) samples with no
sample IDs. `deep-learning/scripts/check_split_integrity.py` checks a JSON
manifest of split IDs for exact overlap, duplicates within a split, group leakage
and temporal ordering, and exits nonzero on failure; its example manifest
`assets/dataset_splits.example.json` fails on purpose (one patient in train and
test, one timestamp violation). Nothing connects the two, so a user who replaces
the synthetic data with a real dataset can train on leaked splits without the
check ever running.

## Objective

When a manifest is supplied, `train_classifier.py` refuses to start training if the
manifest fails the integrity check, and prints why; without a manifest it behaves
as today.

## Scope

### In Scope

- A `--split-manifest PATH` option on `train_classifier.py`.
- Calling the existing check from `check_split_integrity.py`, not copying it.
- Tests for the passing, failing and absent-manifest cases.

### Out of Scope

- Changing what `check_split_integrity.py` checks.
- Real datasets, new models, hyperparameter changes.
- Near-duplicate or content-hash leakage detection.

## Repository Context

Verified by inspection on 2026-10-02:

- `deep-learning/assets/train_classifier.py` is 237 lines, has argparse options
  including `--train-size`, `--val-size`, `--output-dir` and `--seed`, and no
  manifest option.
- `deep-learning/scripts/check_split_integrity.py` exposes `check(payload)`,
  which returns a report with an overall pass/fail, plus `find_overlaps`,
  `find_duplicates`, `find_group_leakage` and `find_temporal_violations`.
- `deep-learning/tests/test_deep_learning_skill.py` imports `check` and the
  `find_*` functions and runs the script as a subprocess;
  `deep-learning/tests/test_assets_smoke.py` runs `train_classifier.py` on CPU.
- `assets/` and `scripts/` are separate folders; whether `assets/` files may
  import from `scripts/` is not established by the repository.

## Technical Approach

1. Decide how `train_classifier.py` reaches `check_split_integrity` (import via
   a path, or run the script as a subprocess); see Open Questions.
2. Add `--split-manifest`; if given, load the JSON, call the check, and exit
   nonzero with the report before any model or DataLoader is built.
3. Keep the default path byte-for-byte equivalent in behavior.
4. Add three tests: the shipped (failing) example manifest blocks training; a
   corrected manifest lets a short run finish; no manifest runs as today.

## Deliverables

- Updated `deep-learning/assets/train_classifier.py`.
- New tests next to the existing ones in `deep-learning/tests/`.
- A line in `deep-learning/README.md` or `SKILL.md` naming the flag, if either
  already documents the template's arguments (not checked here).

## Acceptance Criteria

- `python3 assets/train_classifier.py --split-manifest assets/dataset_splits.example.json`
  exits nonzero before the first epoch and the output names the group leak and
  the temporal violation.
- A manifest that passes the check allows training to start and finish a 1-epoch
  CPU run with the same checkpoint file names (`best.pt`, `last.pt`) as without the
  flag.
- Without `--split-manifest`, the existing smoke test passes unchanged.
- No logic from `check_split_integrity.py` is duplicated in the training script.
- The pre-existing tests in `deep-learning/tests/` still pass.

## Validation

- Run `python3 -m unittest discover -s tests` in `deep-learning/`.
- Run the failing-manifest command above and read the output.
- Run a 1-epoch CPU training with a passing manifest.

## Open Questions

- The synthetic data has no sample IDs, so what does a manifest ID refer to? The
  flag only makes sense once the data source has IDs. **Requires Confirmation**;
  the task assumes the check gates the manifest and the user keeps it consistent
  with their own data loader.
- May a file in `assets/` import from `scripts/`? Skill folders are copied
  whole, so it works if both are present. **Requires Confirmation.**
- What should an unreadable or malformed manifest do? **TBD**; the task assumes it
  also exits nonzero with a message, before any model or output directory exists.
- Should a failing check be overridable (a `--force` flag)? **TBD**; none is
  assumed.

## References

- `deep-learning/assets/train_classifier.py`
- `deep-learning/scripts/check_split_integrity.py`
- `deep-learning/assets/dataset_splits.example.json`
- `deep-learning/tests/test_assets_smoke.py`
- `deep-learning/tests/test_deep_learning_skill.py`
