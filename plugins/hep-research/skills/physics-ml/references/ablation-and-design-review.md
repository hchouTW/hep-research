# Ablation and Design Review Reference

Establishing that a change actually helped. Most reported improvements are confounded,
within seed noise, or bought by a budget the baseline did not get. For the metrics
themselves see [evaluation-metrics.md](evaluation-metrics.md); for evaluation design
see [evaluation-strategy.md](evaluation-strategy.md).

Use `${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/compare_model_runs.py` to test whether a difference survives seed noise.

## Seed variance is the floor

**Run the baseline more than once before comparing anything.** The spread across seeds
of an unchanged configuration is the noise floor, and any improvement smaller than it
is unsupported. This single step invalidates a large fraction of informally reported
gains.

Report the seed distribution, not a single number, and not the best of several runs.
Best-of-N is a biased estimator: its expectation rises with N, so a "best of 5" against
a single baseline run is a comparison of N, not of methods.

## Matched budgets

A comparison is only about the change if everything else is equal:

- **Same compute.** More parameters, more steps, or a longer schedule are confounds,
  not results. Compare at matched FLOPs or matched wall-clock, and say which.
- **Same tuning effort.** A tuned new method against an untuned baseline measures
  tuning. Re-tune the learning rate for *both* - LR interacts with almost every
  architectural change, and an unretuned baseline is the most common single confound.
- **Same data and preprocessing**, including augmentation and tokenization.
- **Same evaluation**, including checkpoint selection. Selecting the best checkpoint on
  the test set leaks; select on validation.

## One change at a time

Bundling changes makes attribution impossible. If several must ship together, ablate
them individually afterward at reduced scale, and say which results are attributed and
which are bundled.

The standard forms:

- **Leave-one-out** - remove each component from the full system. Shows what is
  load-bearing.
- **Add-one-in** - add each component to the baseline. Shows what is sufficient.

These disagree when components interact, and that disagreement is informative rather
than a problem: report both when they differ.

## Statistical discipline

- A difference smaller than the seed spread is **not a result**, whatever the mean says.
- Use **paired comparisons** where possible - the same data, the same splits, the same
  seeds - since pairing removes much of the variance and is far more sensitive.
- Report an **interval on the difference**, not two separate error bars. Overlapping
  individual intervals do not imply a non-significant difference.
- With many variants, some will look good by chance. Either correct for multiplicity or
  confirm the winner on a held-out set.
- Distinguish **statistical significance from practical significance.** A reliable 0.1%
  gain that doubles inference cost is not an improvement.

## Common confounds

| Symptom | Likely confound |
|---|---|
| Gain vanishes on re-run | Seed noise; baseline was one run |
| Gain only on one dataset | Overfitting to that benchmark |
| Gain disappears when baseline LR is retuned | The change was a learning-rate change |
| Gain shrinks with scale | Regularization effect that more data supersedes |
| Gain only with a specific checkpoint | Checkpoint selection on the test set |
| Large gain, tiny model change | Something else changed too - check the diff |

## Reviewing someone else's claim

- What is the baseline, and was it tuned as hard as the proposal?
- How many seeds, and what is the spread?
- Are compute and parameters matched?
- Is the comparison paired, and is the interval on the difference reported?
- Was the test set used for any selection decision?
- Does the ablation isolate the claimed mechanism, or only show the bundle works?
- Does the stated explanation predict anything else that could be checked?

A result that cannot survive these questions is not necessarily wrong - it is
unsupported, which is a different and more common condition.

## Ablation evidence vs. causal explanation

An ablation result is evidence about component *contribution*, not automatically
about *mechanism*. Distinguish:

```text
Removing component X reduces metric Y.
```

from:

```text
The model uses X for reason Z.
```

The second is a stronger, separate claim - it requires the interpretability checks in
[interpretability-and-explainability.md](interpretability-and-explainability.md)
(perturbation, stability, alternative methods), not just the ablation result.

## Deliverables

- Number of seeds and the observed spread for both baseline and variant.
- The matched quantity (FLOPs, wall-clock, or parameters) and confirmation both sides
  were tuned.
- A paired comparison with an interval on the difference.
- Per-component ablation, or an explicit statement that results are bundled.
- The checkpoint-selection rule, confirmed not to involve the test set.
- Practical significance: the cost of the change alongside its benefit.
- Whether any causal/mechanistic claim was made beyond the ablation's own scope, and
  what supports it.
