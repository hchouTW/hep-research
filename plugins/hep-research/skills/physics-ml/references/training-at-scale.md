# Training at Scale Reference

Running a training job that costs real money and time: budgeting it, keeping the
hardware busy, surviving failures, and searching hyperparameters without wasting the
budget. For choosing the parallelism itself see
[parallelism-strategy.md](parallelism-strategy.md); for single-GPU tuning see
[performance-memory.md](performance-memory.md).

Use `${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/estimate_compute_budget.py` to size a run before launching it.

## Budget the run before launching it

Training FLOPs for a transformer are approximately

```
C = 6 * N * D          (N parameters, D tokens; 2 forward + 4 backward)
  + 12 * L * s * h * D (attention score/value matmuls, matters at long sequence)
```

From `C`, wall-clock follows from the aggregate throughput you actually expect:

```
gpu_seconds = C / (peak_flops_per_gpu * MFU)
```

**MFU (model FLOPs utilization)** is the fraction of peak the run actually achieves.
It is the single most useful number for scale work:

| MFU | Reading |
|---|---|
| < 20% | Something is wrong - input pipeline, communication, or excessive recompute |
| 30-50% | Typical for a well-tuned large training run |
| > 60% | Very good; verify the measurement before believing it |

Compute the budget *before* launching. A run that turns out to need three months on the
cluster is a planning failure, not a training failure, and it is visible from a
one-line calculation.

## Compute-optimal sizing

For a fixed compute budget, there is a trade between model size and tokens seen.
Chinchilla-style scaling puts the optimum near **D = 20N** - roughly 20 tokens per
parameter. Training far from that ratio wastes budget:

- `D/N` much below 20: undertrained. A smaller model trained longer would have reached
  the same loss for less compute.
- `D/N` much above 20: overtrained for the compute spent, but this is often the *right*
  choice deliberately, because inference cost scales with `N` and not with `D`. A model
  served billions of times should be smaller and trained longer than compute-optimal.

State which regime you are targeting and why. "Compute-optimal" is optimal for training
cost only.

## Keeping the hardware busy

Diagnose in this order; each step is cheap and rules out a whole class:

1. **Is the GPU idle waiting for data?** Compare step time with and without the real
   dataloader. See [data-loading.md](data-loading.md).
2. **Is it waiting on communication?** Profile a step; look for all-reduce or all-gather
   blocking rather than overlapping backward.
3. **Is recomputation costing more than it saves?** Full recompute adds roughly 30%
   compute; if memory allows selective instead, take it.
4. **Is the batch too small to saturate the GPU?** Small microbatches underuse the
   matrix units; prefer a larger microbatch with fewer accumulation steps when memory
   permits.
5. **Are the kernels themselves slow?** Only now consider `torch.compile`, fused
   optimizers, or attention kernel choice.

## Batch size and learning rate at scale

Scaling data parallelism increases the global batch size, which changes optimization,
not just speed:

- **Linear scaling with warmup** is the standard starting rule: multiply the learning
  rate by the same factor as the batch size, with a warmup of several hundred to a few
  thousand steps. It holds over a useful range and then stops holding.
- **Beyond a critical batch size** additional parallelism buys wall-clock but not sample
  efficiency - each step improves the model less, and total tokens to reach a target
  loss rises. There is no benefit to scaling past it except time.
- **Warmup is not optional at scale.** Large-batch runs diverge in the first few hundred
  steps far more often than they diverge later.
- Gradient accumulation reproduces a large batch on fewer devices, and is the right
  first response to an activation-bound configuration. See
  [training-loop.md](training-loop.md).

## Failures are normal at scale

A multi-day, multi-node run *will* hit hardware faults, preemptions, and stragglers.
Design for it up front:

- **Checkpoint on a wall-clock interval**, not only per epoch, sized so that the
  expected lost work is smaller than the checkpoint cost. See
  [checkpointing.md](checkpointing.md).
- **Checkpoints must be resumable, not just loadable**: model, optimizer, scheduler,
  step count, dataloader position, and RNG state. A resume that restarts the data order
  silently re-trains on the same tokens.
- **Write checkpoints atomically** (temporary file, then rename). A job killed mid-write
  otherwise leaves a corrupt file that fails on resume, hours later.
- **Detect stragglers.** One slow rank sets the pace for every collective; per-rank step
  timing exposes it, aggregate throughput does not.
- **Fail loudly on NaN.** At scale a diverged run can burn a day before anyone looks;
  check loss finiteness every step and abort, rather than logging and continuing.

## Experiment tracking

Once runs are expensive, an untracked run is a wasted one. Record for every run: git
commit, full config, dataset version, random seed, hardware and world size, library
versions, and the resulting curves. See [reproducibility.md](reproducibility.md).

Log throughput and MFU alongside loss. A run whose loss is fine but whose MFU quietly
halved is telling you about an infrastructure regression that the loss curve hides.

## Hyperparameter search under a budget

Full search is unaffordable at scale, so use the structure of the problem:

- **Search small, transfer up.** Tune on a smaller model or a shortened schedule, then
  transfer. Learning rate and batch size transfer reasonably along width when the
  parameterization is designed for it; schedule length and regularization transfer
  poorly.
- **Random beats grid** for a fixed budget when only a few hyperparameters matter,
  which is the usual case.
- **Use early stopping of trials** (successive halving / Hyperband) rather than running
  every trial to completion.
- **Change one thing at a time between full-scale runs.** At this cost, a run that
  changes three things and improves cannot tell you which change helped - see
  [ablation-and-design-review.md](ablation-and-design-review.md).

## Deliverables

- Estimated FLOPs, GPU-hours, wall-clock, and cost, computed before launch.
- Target and achieved MFU, with the throughput measurement that produced it.
- The `D/N` ratio and whether the run is deliberately off compute-optimal, with the
  reason.
- Global batch size, learning-rate scaling rule, and warmup length.
- Checkpoint interval, atomicity, and confirmation that a resume restores data order
  and RNG state.
- Per-rank step timing (straggler check) and a NaN abort.
- The tracked record: commit, config, data version, seed, world size, versions.
