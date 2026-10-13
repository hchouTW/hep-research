# Parallelism Strategy Reference

> Generic ML engineering; not physics-specific. For physics tasks start at
> [ml-analysis.md](ml-analysis.md). Most HEP models fit one GPU, and the answer is DDP
> ([distributed-training.md](distributed-training.md)); read on only when the memory
> equation below says model states or activations do not fit.

Choosing *which* parallelism to use, and in what combination. For DDP and FSDP2
mechanics and launch commands see [distributed-training.md](distributed-training.md); for
single-GPU speed and memory tuning see [performance-memory.md](performance-memory.md).

Use `<plugin root>/skills/physics-ml/scripts/estimate_training_memory.py` to get the numbers below for a concrete
configuration before committing to one.

## Decide in this order

1. **Does one GPU hold the model states?** If yes, use DDP and stop. Do not add
   sharding you don't need - it costs communication and debugging complexity.
2. **Does one GPU hold the model states if the optimizer is sharded?** Use ZeRO-1/2, or
   FSDP2 (`fully_shard`) with `reshard_after_forward=False`.
3. **Do parameters still not fit?** Shard them: ZeRO-3 / FSDP2 full sharding (the
   `fully_shard` default).
4. **Does a single layer not fit, or is the batch latency-bound?** Add tensor
   parallelism, inside a node.
5. **Still out of memory with everything sharded?** Add pipeline parallelism across
   nodes, and accept the bubble.
6. **Are activations, not weights, the binding constraint?** That is a
   recompute/sequence-parallel problem, not a weight-sharding problem - see below.

## The memory equation

Per-GPU training memory is four terms plus fragmentation:

```
params + gradients + optimizer states + activations
```

Bytes per parameter for the first three, at typical settings:

| Setup | Params | Grads | Optimizer | Total/param |
|---|---|---|---|---|
| fp32 + SGD | 4 | 4 | 0 | 8 |
| fp32 + SGD momentum | 4 | 4 | 4 | 12 |
| fp32 + Adam | 4 | 4 | 8 | 16 |
| Mixed precision + Adam (fp32 master) | 2 | 2 | 12 | 16 |
| Mixed precision + 8-bit Adam | 2 | 2 | 6 | 10 |

Mixed precision does **not** halve training memory - it halves the parameter and
gradient terms while the fp32 master weights and moments dominate. It saves activation
memory, which is often the larger effect. See
[mixed-precision.md](mixed-precision.md).

**Activations scale with batch and sequence length, not with parameter count.** This is
why a model that fits at batch 1 fails at batch 32, and why sharding weights does not
help a run that is activation-bound.

## What each strategy shards

| Strategy | Params | Grads | Optimizer | Activations | Extra communication |
|---|---|---|---|---|---|
| DDP | - | - | - | - | gradient all-reduce per step |
| ZeRO-1 | - | - | shard | - | + optimizer state gather |
| ZeRO-2 | - | shard | shard | - | gradient reduce-scatter |
| ZeRO-3 / FSDP2 full sharding | shard | shard | shard | - | parameter all-gather per layer, twice per step |
| Tensor parallel | shard | shard | shard | shard | all-reduce **inside** every layer |
| Pipeline parallel | split | split | split | split by stage | point-to-point between stages |
| Sequence/context parallel | - | - | - | shard | activation exchange along sequence |

## Choosing between them

**DDP** - the default. Replicates everything, communicates gradients once per step,
overlaps that with backward. Cheapest to debug. Fails only when memory runs out.

**FSDP2 / ZeRO-3** - the usual answer for "the model doesn't fit." Communication volume
is roughly 1.5x DDP for full sharding, but it is spread across the step rather than
concentrated. Shard within fast interconnect; a hybrid layout that shards inside a
node and replicates across nodes (a 2-D device mesh, the FSDP1 `HYBRID_SHARD`) usually
beats sharding globally. Parameters become `DTensor`s, and checkpoints go through
distributed checkpoint (DCP); see [distributed-training.md](distributed-training.md).

**Tensor parallel** - splits individual matrix multiplies. Adds an all-reduce *inside
every layer*, so it is viable only over a fast intra-node interconnect. Keep the degree
at or below the number of GPUs per node. It is the only option when one layer alone
exceeds a GPU, and it reduces activation memory, which the ZeRO family does not.

**Pipeline parallel** - splits layers into stages. Cheap communication (activations at
stage boundaries only), so it crosses slow interconnects well, but it introduces a
bubble: with `P` stages and `M` microbatches, the idle fraction is roughly
`(P - 1) / (M + P - 1)`. Keep `M >> P` - at least 4x - or the bubble dominates.

**Sequence/context parallel** - shards the activation memory along the sequence
dimension. Reach for it when long sequences, not weights, are the constraint.

**Composition order.** The conventional nesting is tensor parallel innermost (inside a
node), then pipeline, then data parallel/FSDP outermost. `world_size = TP x PP x DP`,
and getting this factorization wrong is the most common cause of a launch that hangs
rather than errors.

## Activation memory: recompute before you shard

Activation recomputation trades compute for memory and is usually the first thing to
try, before adding a parallelism dimension:

| Mode | Activation memory | Extra compute |
|---|---|---|
| None | full | 0% |
| Selective (attention only) | large reduction | ~5% |
| Full | 2 x h bytes per token per layer (only the bf16 block input of hidden size h is kept) | ~30% |

For comparison, without recomputation a standard transformer layer stores about
`s*b*h*(34 + 5*a*s/h)` bytes (sequence length `s`, micro-batch `b`, hidden size `h`,
`a` heads; Korthikanti et al., arXiv:2205.05198), which is what
`estimate_training_memory.py` uses. Selective recomputation is close to free and should
be the default at scale. See
[custom-autograd-and-hooks.md](custom-autograd-and-hooks.md) for the mechanics.

## Diagnosing the binding constraint

Do not add a parallelism dimension before knowing which term is binding:

- **Optimizer states dominate** (large model, small batch) -> ZeRO-1/2.
- **Parameters dominate** -> ZeRO-3/FSDP, or tensor parallel if one layer is the problem.
- **Activations dominate** (long sequence, large microbatch) -> recompute, smaller
  microbatch with more gradient accumulation, or sequence parallelism. Sharding weights
  will not help.
- **Fragmentation** - allocated memory far below reserved, with OOM anyway. Not a
  parallelism problem; see [performance-memory.md](performance-memory.md).

## Common failures

- Adding FSDP to a run that was activation-bound, and gaining nothing.
- Sharding a 10M-parameter tagger whose real bottleneck is the data loader.
- Tensor parallelism spanning nodes, making every layer wait on the slow link.
- Pipeline stages with too few microbatches, so most GPUs idle.
- Assuming mixed precision halves memory, then sizing the run for a budget it never had.
- `TP x PP x DP != world_size`, which typically hangs at init rather than failing.
- Sharding a model small enough for DDP, and paying communication for nothing.

## Deliverables

- The binding memory term, measured or estimated, before any strategy is chosen.
- The chosen factorization `TP x PP x DP` and its product against `world_size`.
- Which dimensions stay inside a node and why.
- Recomputation mode and its measured compute cost.
- Measured step time against the DDP baseline, so the added complexity is justified by
  a number rather than assumed.
