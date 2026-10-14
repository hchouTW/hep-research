# Architecture Selection Reference

Choosing and sizing an architecture before writing the model code. Implementations:
[transformer-architectures.md](transformer-architectures.md), [sequence-models.md](sequence-models.md),
[generative-models.md](generative-models.md), [particle-and-jet-architectures.md](particle-and-jet-architectures.md);
adapting a model: [transfer-learning.md](transfer-learning.md).

## Strongest baseline first

1. **A pretrained model, fine-tuned.** For images and text it almost always beats a custom architecture trained from
   scratch on a task-sized dataset. For particle and detector data the default is the opposite: train from scratch on
   your own samples and use a pre-trained physics model (which inherits its pre-training simulation) as an ablation -
   see [particle-and-jet-architectures.md](particle-and-jet-architectures.md).
2. **A standard architecture at the right size**, then 3. **a custom one**, justified by structure no standard model
   exploits or by a deployment constraint. The baseline is also what the ablation is measured against.

## Inductive bias against data

| Data structure | Typical choice |
|---|---|
| Fixed-size tabular features (high-level analysis variables) | gradient-boosted trees, then an MLP |
| Unordered sets of particles, hits, tracks | Deep Sets, particle transformers, graph networks (permutation invariant) |
| Irregular relations (hit graphs, detector geometry) | graph networks, message passing |
| Images with translation structure (calorimeter cells on a regular grid) | convolutional networks |
| Ordered, streaming (waveforms, time series) | RNN/GRU/LSTM or a transformer with positions |

A strong bias wins when data are scarce and becomes a ceiling when they are abundant: ask how much simulation there is
before choosing. Symmetry enforcement (exact or approximate, architecture or augmentation):
[geometric-and-equivariant-learning.md](geometric-and-equivariant-learning.md).

## Sizing

Underfitting (training loss plateaus high) is capacity, optimization or data: do not regularize it. Overfitting wants
more simulation, augmentation or regularization before a smaller model. Both losses falling together and stopping
usually means undertrained. Power-law scaling of loss with parameters, data and compute holds within a regime, with
dataset- and architecture-dependent exponents: fit your own learning curve, report the fitted range, and treat
extrapolation beyond about an order of magnitude as a guess with error bars; published language-model ratios do not
transfer ([training-at-scale.md](training-at-scale.md)). Deployment cost is set by parameters: a model run on every
event in reconstruction or a trigger is usually smaller than the best offline model, often distilled from it; decide
before training. Pre-norm residual blocks make depth trainable; very deep and narrow is harder to train; tiny per-head
dimensions degrade attention.

## Budget and review

Know the parameter count, training cost, per-GPU memory and inference latency before building
(`estimate_training_memory.py`, `estimate_compute_budget.py`, [serving-architecture.md](serving-architecture.md)). In
review ask: what baseline does it beat and was it tuned as hard; which change does the work and what separates it from
the others; does it fit the deployment budgets; what would make it fail, and was that checked.
