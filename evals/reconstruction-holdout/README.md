# Reconstruction holdout scorer (T13)

`score_holdout.py` is the frozen scorer of the detector-reconstruction AI evaluation holdout (plan v9.2 T13, K11,
R22). `FROZEN.sha256` records its SHA-256 and that of its tests. Any change to either is a new scorer, and must come
before a holdout exists.

No holdout file, task, answer or run record is ever placed in this folder or anywhere in the repository. The tests use
synthetic, obviously fake fixtures only.

- Harness, custody and blocked states: `plugins/hep-research/docs/dev/detector-reconstruction/t13-harness-spec.md`
- What the holdout writer receives: `plugins/hep-research/docs/dev/detector-reconstruction/t13-holdout-writer-brief.md`
- Tests: `python -m unittest discover -s evals/reconstruction-holdout/tests -t evals/reconstruction-holdout/tests`
