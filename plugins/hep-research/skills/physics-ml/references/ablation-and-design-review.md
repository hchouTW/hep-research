# Ablation and Design Review Reference

Establishing that a change helped. Most reported improvements are confounded, within seed noise, or bought by a budget
the baseline did not get. Test: `<plugin root>/skills/physics-ml/scripts/compare_model_runs.py` (paired comparison
across seeds; with fewer than 10 seeds it decides with a Student-t interval on the seed means and reports the exact permutation p-value).

- **Seed variance is the floor.** Run the baseline more than once; an improvement smaller than the spread of an
  unchanged configuration is unsupported. Report the distribution, never best-of-N (its expectation rises with N).
- **Matched budgets:** the same compute (FLOPs or wall-clock, say which), the same tuning effort (re-tune the learning
  rate for both: an untuned baseline is the most common confound), the same data and preprocessing, the same
  evaluation and checkpoint selection on validation.
- **One change at a time.** Bundled changes cannot be attributed; ablate them afterwards (leave-one-out shows what is
  load-bearing, add-one-in what is sufficient; disagreement between the two reveals interactions).
- **Statistics:** pair the comparison (same data, splits, seeds), report an interval on the difference (overlapping
  individual error bars do not imply no difference), correct for many variants or confirm the winner on a held-out
  set, and weigh practical against statistical significance (a reliable 0.1% gain that doubles inference cost is not
  an improvement).

| Symptom | Likely confound |
|---|---|
| gain vanishes on a re-run | seed noise, one baseline run |
| gain disappears when the baseline LR is retuned | the change was a learning-rate change |
| gain shrinks with scale | a regularization effect superseded by more data |
| gain only for one checkpoint | checkpoint selection on the test set |
| large gain from a tiny change | something else changed: check the diff |

An ablation shows a component's contribution, not its mechanism: "the model uses X for reason Z" needs the checks in
[interpretability-and-explainability.md](interpretability-and-explainability.md). Deliver seeds and spreads, the
matched quantity, the paired interval, per-component ablations (or a statement that results are bundled), the
checkpoint rule, and the cost of the change beside its benefit.
