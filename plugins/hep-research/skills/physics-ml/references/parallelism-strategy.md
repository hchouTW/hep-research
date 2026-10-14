# Parallelism Strategy Reference

> Generic ML engineering. Most HEP models fit one GPU and the answer is DDP
> ([distributed-training.md](distributed-training.md)); read on only when the memory equation says model states or
> activations do not fit. Numbers for a configuration: `<plugin root>/skills/physics-ml/scripts/estimate_training_memory.py`.
> Single-GPU tuning: [performance-memory.md](performance-memory.md).

## Decide in this order

1. One GPU holds the model states: DDP, stop. 2. It does with the optimizer sharded: ZeRO-1/2 or FSDP2 with
`reshard_after_forward=False`. 3. Parameters still do not fit: ZeRO-3 / FSDP2 full sharding. 4. One layer does not
fit, or the batch is latency-bound: tensor parallelism inside a node. 5. Still out of memory: pipeline parallelism
across nodes, accepting the bubble. 6. Activations, not weights, bind: recompute, smaller microbatch, or sequence
parallelism; sharding weights will not help.

## The memory equation (the one home of these numbers)

Per-GPU memory = params + gradients + optimizer states + activations (+ fragmentation). Bytes per parameter:

| Setup | Params | Grads | Optimizer | Total/param |
|---|---|---|---|---|
| fp32 + SGD | 4 | 4 | 0 | 8 |
| fp32 + SGD momentum | 4 | 4 | 4 | 12 |
| fp32 + Adam | 4 | 4 | 8 | 16 |
| Mixed precision + Adam (fp32 master) | 2 | 2 | 12 | 16 |
| Mixed precision + 8-bit Adam | 2 | 2 | 6 | 10 |

So a 3B model needs about 48 GB per replica under plain DDP with mixed-precision Adam. Mixed precision does not halve
training memory: it halves parameters and gradients while fp32 master weights and moments dominate, and it saves
activation memory ([mixed-precision.md](mixed-precision.md)). Activations scale with batch and sequence length, not
parameter count: without recomputation a transformer layer stores about `s b h (34 + 5 a s / h)` bytes (Korthikanti
et al., arXiv:2205.05198), which `estimate_training_memory.py` uses; full recomputation keeps about `2 h` bytes per
token per layer for about +30% compute, selective recomputation (attention only) costs about 5%.

## What each strategy shards

| Strategy | Shards | Extra communication |
|---|---|---|
| DDP | nothing | gradient all-reduce per step |
| ZeRO-1 / ZeRO-2 | optimizer / + gradients | state gather / gradient reduce-scatter |
| ZeRO-3 / FSDP2 full | params, grads, optimizer | parameter all-gather per layer, twice per step (about 1.5x DDP volume) |
| Tensor parallel | all, inside each layer | all-reduce inside every layer: intra-node only |
| Pipeline parallel | layers by stage | point-to-point; bubble about (P-1)/(M+P-1), keep M >= 4P |
| Sequence/context parallel | activations along the sequence | activation exchange |

Nest tensor parallel innermost, then pipeline, then data parallel; `TP x PP x DP = world_size`, and a wrong
factorization usually hangs at init. Shard within fast interconnect and replicate across nodes (a 2-D mesh). FSDP2
parameters are `DTensor`s with distributed checkpoints ([distributed-training.md](distributed-training.md)).

## Common failures

FSDP on an activation-bound run; sharding a 10M-parameter tagger whose bottleneck is the loader; tensor parallelism
across nodes; too few pipeline microbatches; assuming mixed precision halves memory; fragmentation (allocated far
below reserved) mistaken for a parallelism problem. Deliver the binding term, the factorization, which dimensions stay
inside a node, the recompute mode and its cost, and step time against the DDP baseline.
