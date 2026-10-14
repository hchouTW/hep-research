# Optimization and Training Dynamics Reference

Diagnosing why training fails instead of changing hyperparameters at random. Loop mechanics:
[training-loop.md](training-loop.md); shape, device and NaN errors: [debugging-pytorch.md](debugging-pytorch.md);
scaling rules: [training-at-scale.md](training-at-scale.md); sizing: [architecture-selection.md](architecture-selection.md).

## Classify the failure first

| Class | Signature | Where the fix is |
|---|---|---|
| Implementation | cannot overfit a tiny batch | loss wiring and label format ([deep-learning-guide.md](deep-learning-guide.md), loss table), gradient flow |
| Numerical | NaN or inf, exploding norms | gradients below, [debugging-pytorch.md](debugging-pytorch.md) |
| Optimization | tiny batch overfits; full loss stuck or plateaus early | learning rate, schedule, initialization, normalization |
| Capacity | train and validation loss fall together and plateau high | sizing |
| Data | stalls whatever the architecture or LR | [data-strategy.md](data-strategy.md) |
| Generalization | train good, validation bad | leakage and splits ([ml-analysis.md](ml-analysis.md)), regularization |
| Objective mismatch | loss improves, the target metric does not | [evaluation-metrics.md](evaluation-metrics.md) |

Flow: overfit 8-32 examples without augmentation or regularization. If that fails, it is implementation (check the
loss, `requires_grad`, non-zero gradients) before any LR change. If it passes and train falls while validation does
not, it is generalization: the optimizer is doing its job. Otherwise suspect optimization before capacity.

## Levers and their interactions

- **Learning rate** dominates: too high oscillates or diverges after progress; too low looks like a capacity failure
  until compared with a higher-LR run.
- **Batch size** changes gradient variance; batch/LR co-scaling is a hypothesis to check
  ([training-at-scale.md](training-at-scale.md)).
- **Warmup:** a run that diverges only in its first few hundred steps has a warmup problem (deep models, large
  batches, Adam-family second moments).
- **Gradient accumulation** reproduces large-batch statistics, except in layers with per-microbatch statistics
  (BatchNorm).
- **Clipping** treats a symptom; if it fires on most steps, fix the LR or initialization.
- **Weight decay** is L2 only for plain SGD: `weight_decay=` on `torch.optim.Adam` is L2, `AdamW` decouples it; do
  not compare runs that mix them.

## Initialization, normalization, gradients

Residual connections and normalization make depth trainable (pre-norm beyond a few layers). A loss stuck at the
uniform-output value (`-log(1/num_classes)`) means the model has not started learning: check initialization scale and
whether gradients reach early layers (backward hooks, [custom-autograd-and-hooks.md](custom-autograd-and-hooks.md))
before blaming capacity or data. Localize vanishing or exploding gradients per layer with hooks; persistent vanishing
gradients need an architectural fix (normalization, residuals, activation), not a lower LR. RNNs are most exposed
([sequence-models.md](sequence-models.md)).

## Plateaus, collapse, forgetting

A plateau after progress is more often the LR schedule or capacity than the data. Representation collapse (distinct
inputs mapped to near-identical representations; VAE posterior and GAN mode collapse in
[generative-models.md](generative-models.md)) also occurs in self-supervised setups. Forgetting and instability in
fine-tuning call for a lower LR and sometimes frozen early layers ([transfer-learning.md](transfer-learning.md)).

Deliver the failure class with the tiny-batch result that supports it, the LR, schedule, warmup and batch values used,
the layers where hooks localized a gradient problem, the weight-decay form and optimizer, and which classes were ruled
out and how.
