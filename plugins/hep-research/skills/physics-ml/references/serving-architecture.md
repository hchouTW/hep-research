# Serving Architecture Reference

> Generic ML engineering; not physics-specific. For physics tasks start at
> [ml-analysis.md](ml-analysis.md). Deployment inside experiment software and hardware
> triggers (score agreement, FPGA latency, trigger systematics) is in ml-analysis.md,
> "Deployment in experiment software and triggers"; this file is for a model run as a
> service, for example a GPU inference server called by many reconstruction or
> analysis jobs.

Sizing and shaping inference as a service. For the export mechanics (ONNX,
`torch.export`, AOTInductor, `torch.compile`) see
[export-and-deployment.md](export-and-deployment.md).

Use `<plugin root>/skills/physics-ml/scripts/serving_capacity.py` to size replicas against a latency and throughput
target.

## State the budget first

Three numbers, before any optimization:

- **Latency target**, as a percentile, not a mean (p99 for a service; a hard upper bound
  for anything in a trigger path).
- **Throughput target** at peak: events or requests per second from all client jobs
  running at once, not the average.
- **Cost ceiling**: GPU-hours or the share of a site's coprocessors you may occupy.

Optimizations trade against each other, so without the budget there is no way to know
which trade is right. Larger batches raise throughput and *raise* latency; quantization
lowers both latency and cost while risking quality.

## Latency has parts

```
total = queueing + batching wait + compute + network + pre/post-processing
```

Measure them separately. Queueing is a capacity problem, not a model problem. Input
conversion (building particle tensors from the event data model, padding, serialization
over the network) is frequently comparable to model compute for small models, and is
invisible if only GPU time is profiled.

## Batching

Batching is the main throughput lever and the main latency cost.

- **Static batching** wastes capacity on partially-filled batches under variable load.
- **Dynamic batching** collects requests up to a size or a timeout. The timeout is the
  latency you are choosing to add; set it from the budget, not by default.
- With variable particle multiplicity, bucket requests by size or use dynamic axes
  ([export-and-deployment.md](export-and-deployment.md)), so a batch is not padded to its
  largest event.

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

**Every accuracy-affecting technique requires a measured comparison of scores on the
same events**, at the working point and in the phase-space regions the analysis uses,
not only an aggregate metric - see [evaluation-strategy.md](evaluation-strategy.md) and
the deployment checks in [ml-analysis.md](ml-analysis.md).

## Hardware and capacity

Choose hardware from the binding constraint. Small-batch inference is usually
**memory-bandwidth-bound**, not compute-bound, so a device with higher peak FLOPs but
equal bandwidth may not help at all. CPU inference is viable and cheaper for small
models, which is the common case for taggers run inside reconstruction.

Capacity planning needs peak load, not average; the latency budget at that peak;
headroom for failover; and warmup time, since a cold replica with compilation may take
minutes.

## Deliverables

- Latency target, throughput at peak, and cost ceiling.
- Latency decomposed into queueing, batching, compute, network, and pre/post-processing.
- Batching strategy and the timeout, justified against the latency budget.
- Scores compared on identical events after any accuracy-affecting optimization.
- Replica count with utilization headroom, and measured warmup time.
