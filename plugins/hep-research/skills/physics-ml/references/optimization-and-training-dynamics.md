# Optimization and Training Dynamics Reference

Diagnosing *why* training is failing rather than changing hyperparameters at random.
For the mechanical training-loop shape see [training-loop.md](training-loop.md); for
shape/device/dtype/NaN debugging see [debugging-pytorch.md](debugging-pytorch.md); for
batch-size/LR scaling and warmup at large scale see
[training-at-scale.md](training-at-scale.md); for capacity/sizing against data see
[architecture-selection.md](architecture-selection.md).

## Training failure classification

Before changing anything, classify the failure. Each class has a different fix, and
treating one class's symptom with another class's fix wastes runs:

| Class | Signature | Fix lives in |
|---|---|---|
| Implementation failure | Can't even overfit a tiny batch | This file's diagnostic flow, [debugging-pytorch.md](debugging-pytorch.md) |
| Numerical failure | Loss/grads are NaN or inf, or explode | This file's gradient section, [debugging-pytorch.md](debugging-pytorch.md) |
| Optimization failure | Tiny-batch overfit works; full training loss won't move or plateaus early | This file's LR/init/normalization sections |
| Capacity failure | Train and val loss fall together and plateau high | [architecture-selection.md](architecture-selection.md) sizing |
| Data failure | Loss won't move, or moves then stalls, independent of architecture/LR changes | [data-strategy.md](data-strategy.md) |
| Generalization failure | Train loss good, val loss bad or diverging | [data-strategy.md](data-strategy.md), this file's regularization notes |
| Objective mismatch | Loss improves, target metric doesn't | [evaluation-metrics.md](evaluation-metrics.md), [evaluation-strategy.md](evaluation-strategy.md) |

## Diagnostic flow

```text
Loss is not improving
        |
Can the model overfit a tiny batch (8-32 examples, no augmentation/regularization)?
        |
       No  -> implementation failure: check loss wiring, label format vs. loss
              (see deep-learning-guide.md Task -> Loss/Output Conventions), gradient flow
              (are all intended parameters requires_grad and receiving nonzero
              grad?), and numerical issues (below) before touching LR.
        |
       Yes
        |
Does training loss fall while validation loss does not (or rises)?
        |
       Yes -> generalization failure: inspect leakage, data distribution,
              capacity, regularization - see [data-strategy.md](data-strategy.md).
              Do not assume optimization is broken; the optimizer is doing its job.
        |
       No  -> optimization or capacity failure: check LR/schedule/init/
              normalization (below) before assuming the model is too small.
              A model that is definitely too small will underfit even a tiny
              batch in the step above - if that step passed, suspect
              optimization first.
```

Adapt the tiny-batch size and iteration count to the task; the point is a fast, cheap
test that isolates implementation correctness from everything else.

## Gradient and optimizer behavior

Reason about the *interaction* among these, not each in isolation - changing one
without the others is a common source of confounded conclusions (see
[ablation-and-design-review.md](ablation-and-design-review.md)):

- **Learning rate** is the dominant lever. Too high: loss oscillates or diverges after
  initial progress. Too low: loss falls but implausibly slowly, indistinguishable from
  a capacity failure without a comparison run at a higher LR.
- **Batch size** changes gradient variance, not just throughput - a smaller batch has
  noisier gradients, which can help escape sharp minima or can just slow convergence.
  Treat batch-size/LR co-scaling as a hypothesis to check on this run, not a guaranteed
  transfer from another model or paper - see
  [training-at-scale.md](training-at-scale.md) for the scale-specific rule and its
  limits.
- **Warmup** matters most when the model is deep, the batch is large, or the
  optimizer's second-moment estimate is still noisy early on (Adam-family). A run that
  diverges only in the first few hundred steps and is fine afterward is a warmup
  problem, not an LR problem.
- **Gradient accumulation** reproduces a larger batch's *statistics* on less memory, but
  not its wall-clock - if a run behaves differently with accumulation on vs. an
  equivalent real batch, suspect a normalization layer computing per-microbatch
  statistics (e.g. BatchNorm) rather than the accumulation logic itself.
- **Gradient clipping** treats a symptom (occasional large-norm updates), not the
  underlying cause. If clipping is firing on most steps rather than rare ones, the
  underlying LR or initialization is the actual problem.
- **Weight decay vs. L2 regularization** are equivalent for plain SGD but **not** for
  Adam-family optimizers, where L2 added to the loss interacts with the adaptive
  learning rate and decoupled weight decay (as in AdamW) does not. Using
  `weight_decay=` on `torch.optim.Adam` is L2, not decoupled weight decay; use `AdamW`
  for the decoupled form. Don't treat the two as interchangeable when comparing runs.

## Initialization and normalization

- **Residual connections and normalization are what make depth trainable** - see
  [architecture-selection.md](architecture-selection.md)'s note on pre-norm vs.
  post-norm. A deep model that fails to train at all, and passes the tiny-batch test
  once made shallow, points here before pointing at LR.
- A loss that is finite but stuck exactly at the value implied by uniform-random output
  (e.g. `-log(1/num_classes)` for classification) past the first few steps indicates
  the model has not started learning at all - check initialization scale and whether
  gradients are actually reaching the early layers (see hooks in
  [custom-autograd-and-hooks.md](custom-autograd-and-hooks.md)) before assuming this is
  a capacity or data problem.
- Non-default initialization is justified when the architecture is non-standard enough
  that framework defaults were not designed for it (unusual depth, custom layer types).
  Otherwise, prefer framework defaults over hand-tuned initialization - they are usually
  already appropriate for the layer type.

## Vanishing and exploding gradients

- Localize before fixing: use `register_full_backward_hook` (see
  [custom-autograd-and-hooks.md](custom-autograd-and-hooks.md)) on a few layers to see
  where gradient magnitude collapses toward zero or blows up, rather than guessing from
  the aggregate loss curve.
- Recurrent architectures are more exposed to both failure modes than attention/
  feed-forward stacks - see [sequence-models.md](sequence-models.md) for RNN-specific
  clipping and gating guidance.
- Persistent vanishing gradients despite clipping and warmup usually mean the fix is
  architectural (normalization placement, residual connections, activation choice), not
  a further LR reduction.

## Training plateaus, collapse, and forgetting

- **A plateau that appears after initial progress** is more often a capacity or LR-
  schedule issue (LR decayed too early/late) than a data issue - check where in the
  schedule the plateau starts before changing the data pipeline.
- **Representation collapse** - the model maps distinct inputs to near-identical
  internal representations - is not unique to generative models. The VAE posterior
  collapse and GAN mode collapse in [generative-models.md](generative-models.md) are
  specific, well-characterized instances; the same underlying pattern (loss looks fine,
  outputs/representations lack diversity) shows up in self-supervised and contrastive
  setups too - see [interpretability-and-explainability.md](interpretability-and-explainability.md)
  for representation-specific diagnostics.
- **Catastrophic forgetting** during fine-tuning (performance on the original task
  degrades while the new task improves) and general **fine-tuning instability** (loss
  spikes early in fine-tuning) usually call for a lower learning rate than training
  from scratch, and sometimes for freezing early layers - see
  [transfer-learning.md](transfer-learning.md) and
  [efficient-finetuning.md](efficient-finetuning.md).

## Deliverables

- The failure classified into one of the classes above, with the tiny-batch overfit
  result that supports the classification.
- If optimization-related: the LR/schedule/warmup/batch-size values actually used and
  what varying each one changed.
- If gradient-related: the layer(s) where hooks localized the vanishing/exploding
  behavior.
- Whether weight decay or L2 was used, and with which optimizer.
- A statement of which class was *ruled out* and how, not only which was found.
