# Serving Architecture Reference

Sizing and shaping inference in production. For the export mechanics (TorchScript,
ONNX, `torch.compile`) see
[export-and-deployment.md](export-and-deployment.md); for quantization as a training
concern see [efficient-finetuning.md](efficient-finetuning.md).

Use `${CLAUDE_PLUGIN_ROOT}/skills/physics-ml/scripts/serving_capacity.py` to size replicas against a latency and throughput
target.

## State the budget first

Three numbers, before any optimization:

- **Latency target**, as a percentile, not a mean. p99 is what users experience; a mean
  hides the tail that causes timeouts.
- **Throughput target** in requests/second, at peak rather than average.
- **Cost ceiling**, per million requests or per month.

Optimizations trade against each other, so without the budget there is no way to know
which trade is right. Larger batches raise throughput and *raise* latency; quantization
lowers both latency and cost while risking quality.

## Latency has parts

```
total = queueing + batching wait + compute + network + pre/post-processing
```

Measure them separately. Teams routinely optimize the compute term while queueing
dominates - and queueing is a capacity problem, not a model problem. Tokenization,
image decoding, and serialization are frequently comparable to model compute for small
models, and are invisible if only GPU time is profiled.

## Batching

Batching is the main throughput lever and the main latency cost.

- **Static batching** wastes capacity on partially-filled batches under variable load.
- **Dynamic batching** collects requests up to a size or a timeout. The timeout is the
  latency you are choosing to add; set it from the budget, not by default.
- **Continuous batching** (for autoregressive generation) admits new requests as others
  finish rather than waiting for the whole batch. It is a large throughput win when
  sequence lengths vary, which they always do.

**Utilization above roughly 80% causes queueing delay to grow sharply.** Sizing a
service to run near 100% utilization produces a p99 far worse than the arithmetic
suggests - provision headroom deliberately.

## Making the model cheaper

In rough order of return per unit of risk:

| Technique | Typical gain | Cost |
|---|---|---|
| Right-sizing the model | Large | Requires retraining or a smaller checkpoint |
| Quantization (int8/fp8) | 2-4x memory and often latency | Small quality loss; must be measured |
| Distillation | Large | A separate training pipeline |
| Compilation / kernel fusion | 1.5-3x | Build complexity, warmup cost |
| KV caching (generation) | Very large | Memory scales with concurrency x sequence |
| Speculative decoding | 2-3x for generation | A draft model and added complexity |

**Every accuracy-affecting technique requires a measured quality comparison on the
production distribution**, not a benchmark. Quantization that costs 0.2% on a
benchmark can cost far more on a specific slice - see
[evaluation-strategy.md](evaluation-strategy.md).

For generation, **KV cache memory, not weights, usually limits concurrency.** It grows
with batch size times sequence length, so maximum concurrency falls as context grows.
Size it explicitly.

## Hardware and capacity

Choose hardware from the binding constraint. Small-batch inference is usually
**memory-bandwidth-bound**, not compute-bound, so a device with higher peak FLOPs but
equal bandwidth may not help at all. Large-batch and long-prefill work is
compute-bound. CPU inference is viable and cheaper for small models.

Capacity planning needs peak load, not average; the latency budget at that peak;
headroom for failover; and warmup time, since a cold replica with compilation may take
minutes and cannot absorb a traffic spike.

## Deliverables

- Latency target as a percentile, throughput at peak, and cost ceiling.
- Latency decomposed into queueing, batching, compute, network, and pre/post-processing.
- Batching strategy and the timeout, justified against the latency budget.
- For generation: KV cache memory and the resulting concurrency limit.
- Quality measured on the production distribution after any accuracy-affecting
  optimization.
- Replica count with utilization headroom, and measured warmup time.
