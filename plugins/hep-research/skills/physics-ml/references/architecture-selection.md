# Architecture Selection Reference

Choosing and sizing an architecture before writing the model code. For the
implementation of specific architectures see
[transformer-architectures.md](transformer-architectures.md),
[sequence-models.md](sequence-models.md), and
[generative-models.md](generative-models.md); for adapting an existing model see
[transfer-learning.md](transfer-learning.md).

## Start from the strongest baseline, not from the architecture

In order of what usually wins:

1. **A pretrained model, fine-tuned.** Almost always beats a custom architecture
   trained from scratch on a task-sized dataset. This should be the default and the
   thing a novel architecture must beat.
2. **A standard architecture at the right size.** Established blocks with a sensible
   parameter count.
3. **A custom architecture.** Justified when the data has structure no standard model
   exploits, or when a deployment constraint (latency, memory, hardware) rules the
   standard options out.

Reaching for (3) before establishing (1) is the most common and most expensive
architecture mistake. The baseline is also what the eventual ablation is measured
against, so it is not wasted work either way.

## Match inductive bias to data structure

| Data structure | Bias that helps | Typical choice |
|---|---|---|
| Local spatial correlation, translation invariance | Locality, weight sharing | Convolutional |
| Long-range dependence, variable-length | Global mixing, content-based routing | Transformer |
| Strictly ordered, streaming, small data | Recurrence, bounded state | RNN/GRU/LSTM |
| Irregular relations between entities | Permutation invariance, message passing | Graph network |
| Fixed-size tabular features | Little structure to exploit | Gradient boosting, then MLP |

The trade is data-dependent: a strong inductive bias wins when data is scarce and
becomes a ceiling when data is abundant. Transformers beat convolutional models on
vision at large scale and lose at small scale for exactly this reason. **Ask how much
data there is before choosing.** For genuinely tabular problems, a gradient-boosted
tree is frequently the right answer and a neural network is not.

When the inductive bias in question is a symmetry (permutation, rotation, a physics
group like Lorentz), the enforcement decision - architecture vs. augmentation vs.
objective, and whether it should be exact or approximate - has its own reasoning
sequence; see
[geometric-and-equivariant-learning.md](geometric-and-equivariant-learning.md).

## Sizing: capacity against data

- **Underfitting** (training loss plateaus high) is a capacity, optimization, or data
  problem. Increase capacity or fix optimization first; regularization makes it worse.
- **Overfitting** (training loss falls, validation rises) means capacity exceeds what
  the data supports. More data, augmentation, or regularization - reducing size is the
  last resort, since it also lowers the ceiling.
- **Neither** - both losses fall together and stop - usually means the run is
  undertrained rather than the model too small. Train longer before growing it.

At scale the sizing question becomes compute allocation rather than fit: for a fixed
budget, a smaller model on more tokens and a bigger model on fewer tokens reach
different losses, and the optimum is near 20 tokens per parameter. See
[training-at-scale.md](training-at-scale.md).

**Deployment cost is set by parameters, training cost by parameters times tokens.** A
model served at high volume should usually be smaller and trained longer than
compute-optimal. Decide this before training, not after.

## Depth, width, and shape

- **Depth** buys compositional expressiveness; **width** buys capacity per layer and
  uses hardware better. Very deep and narrow is usually harder to train and slower per
  parameter than the reverse.
- **Residual connections and normalization are what make depth trainable.** Pre-norm
  transformer blocks are markedly more stable at depth than post-norm; this is a
  trainability decision, not a quality one.
- **Aspect ratios far from convention are a red flag.** Standard shapes exist because
  they were searched. Deviating needs a reason.
- **Head count** trades number of attention subspaces against dimension per head. Very
  small per-head dimension degrades quality.

## Scaling laws, and their limits

Loss falls predictably as a power law in parameters, data, and compute over a wide
range, which makes it possible to fit a curve on small runs and extrapolate.

Use them, with the caveats:

- The exponents are **dataset- and architecture-dependent**. Fit your own on your own
  data; a published constant is not transferable.
- They predict **loss**, not downstream task performance, and the relationship between
  the two is not monotonic for every task.
- They hold **within a regime**. Changing tokenizer, data mixture, or objective changes
  the curve.
- Extrapolating more than about an order of magnitude beyond the fitted range is a
  guess with error bars, and should be stated as one.

## Budget before building

Before writing the model, know: parameter count, training FLOPs and cost, per-GPU
memory under the intended parallelism, and inference latency and cost at the target
batch size. `${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/estimate_training_memory.py` and
`${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/estimate_compute_budget.py` give the first three;
[serving-architecture.md](serving-architecture.md) covers the fourth.

An architecture that cannot be trained in the available time, or served within the
latency budget, is not a candidate however good it looks.

## Reviewing an architecture proposal

Distinct from reviewing model code - see the code checklist in `deep-learning-guide.md`. Ask:

- What baseline does this beat, and was that baseline tuned as hard as this?
- What is the parameter count, training cost, and inference latency?
- Which change is doing the work, and what evidence separates it from the others?
- Does it fit the memory and latency budgets under the intended deployment?
- What has to be true for this to fail, and was that checked?
- Is a pretrained model available that would make this unnecessary?

## Deliverables

- The baseline the architecture is measured against, and how hard it was tuned.
- Data scale, and the inductive bias justified against it.
- Parameter count, training FLOPs/cost, per-GPU memory, and inference latency.
- Depth/width/head choices, with any non-standard shape justified.
- If scaling laws were used: the runs they were fitted on and the extrapolation range.
- Whether the model is deliberately off compute-optimal for inference reasons.
