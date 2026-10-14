# Training at Scale Reference

> Generic ML engineering. The failure handling and tracking apply to any multi-day job on a batch cluster. The FLOP
> formula is written for transformers, where D counts tokens (for a particle transformer, particles seen). Parallelism
> choice: [parallelism-strategy.md](parallelism-strategy.md); single-GPU tuning: [performance-memory.md](performance-memory.md).
> Sizing: `<plugin root>/skills/physics-ml/scripts/estimate_compute_budget.py`.

## Budget before launch

`C = 6 N D` (N parameters, D tokens) `+ 12 L s h D` (attention, at long sequence); `gpu_seconds = C / (peak_flops x MFU)`.
MFU (model FLOPs utilization) below 20% means a pipeline, communication or recompute problem; 30-50% is typical of a
well-tuned large run; above 60%, verify the measurement. Compute-optimal ratios (about 20 tokens per parameter) were
fitted on language models and do not transfer: size a physics model from a learning curve on your own data (two or
three model sizes against two or three training-set sizes; more simulation is often cheaper than a larger model).

## Keeping the hardware busy

Diagnose in order: GPU waiting for data ([data-loading.md](data-loading.md)); communication blocking instead of
overlapping backward; recomputation costing more than it saves (full recompute about +30%); microbatch too small;
only then kernels (`torch.compile`, fused optimizers, attention kernels). Log throughput and MFU beside the loss: a
halved MFU with a fine loss is an infrastructure regression.

## Batch size and learning rate

Linear scaling with warmup is the usual starting rule for SGD-like optimizers; for Adam-type optimizers a
square-root scaling of the learning rate with the batch size is also used (`unverified`: no opened source cited
here; tune on a short schedule). Beyond a critical batch size more data parallelism buys wall-clock but not sample
efficiency. Large-batch runs diverge early: warmup is not optional. Gradient accumulation reproduces a large batch on
fewer devices ([training-loop.md](training-loop.md)).

## Failures are normal

Checkpoint on a wall-clock interval, resumably (model, optimizer, scheduler, GradScaler, step, data position, RNG) and
atomically (temporary file, then `os.replace`): [checkpointing.md](checkpointing.md). Time each rank (one straggler
sets the pace), and abort on a non-finite loss instead of logging it. Track commit, config, dataset version, seed,
world size and library versions ([reproducibility.md](reproducibility.md)).

## Hyperparameter search under a budget

Tune small and transfer up (learning rate and batch size transfer along width when the parameterization is built for
it; schedule length and regularization transfer poorly); random search beats grid when few hyperparameters matter;
stop poor trials early (successive halving, Hyperband); between full-scale runs change one thing at a time
([ablation-and-design-review.md](ablation-and-design-review.md)). For physics data the search uses grouped (or nested,
grouped) cross-validation: [ml-analysis.md](ml-analysis.md), "Hyperparameter search".
